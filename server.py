import os
import logging
from typing import List, Dict, Any, Optional

from fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import AzureOpenAI
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse, HTMLResponse
import os

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy third-party logs
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

mcp = FastMCP(
    name="Flame Knowledge Base",
    on_duplicate_tools="error",
)

# Static files are served through custom routes below

# Initialize clients
def _init_clients():
    """Initialize Azure OpenAI and Qdrant clients."""
    try:
        # Initialize Azure OpenAI client
        openai_client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("OPENAI_API_BASE"),
        )
        
        # Initialize Qdrant client
        qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_HOST"),
            port=os.getenv("QDRANT_PORT"),
        )
        
        collection_name = os.getenv("COLLECTION_NAME", "flame_docs")
        
        return openai_client, qdrant_client, collection_name
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        raise

# Global client instances
openai_client, qdrant_client, collection_name = _init_clients()

def _create_query_embedding(query: str) -> List[float]:
    """Create embedding for search query."""
    try:
        response = openai_client.embeddings.create(
            input=[query],
            model=os.getenv("OPENAI_MODEL_NAME", "text-embedding-3-small"),
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to create embedding for query: {e}")
        raise

@mcp.tool(
    name="get_flame_knowledge",
    tags={},
)
def get_flame_knowledge(
    query: str,
    version: str | None = None,
    limit: int = 5,
    min_score: float = 0.4,
) -> list:
    """
    This tool retrieves a list of relevant knowledge based on the provided query.
    The knowledge base is backed by Qdrant with semantic similarity search.
    You should start with a smaller limit and a higher min_score. If you think the result is not good enough, you can then re-call this tool with a higher limit and a lower min_score.
    If user asks anything related to the Flame engine, including api and class references, if you are not confident, this function should be called.
    If there is any conflict between your knowledge and the queried knowledge, the queried knowledge should be considered more reliable.
    Only call this function if you are certain it's about Flame engine.
    
    Args:
        query: search query related to Flame engine (can be descriptive, e.g., "menu screen UI components")
        version: optional version filter (e.g., "1.29.0")
        limit: maximum number of results to return (default: 5)
        min_score: minimum similarity score threshold (default: 0.4 for broader results)

    Returns:
        list of relevant Flame documentation/references snippets
    """
    try:
        logger.info(f"Searching Flame knowledge base for: '{query}'")
        
        # Create embedding for the query
        query_embedding = _create_query_embedding(query)
        
        # Build search filter - only filter by version if specified
        search_filter = None
        if version:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="version",
                        match=MatchValue(value=version)
                    )
                ]
            )
        
        # Perform broader similarity search with lower threshold
        search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=min(limit * 2, 30),  # Search more broadly first
            score_threshold=max(min_score - 0.1, 0.2),  # Even lower threshold for initial search
            with_payload=True,
        )
        
        # Enhanced result ranking with metadata-based boosting
        enhanced_results = []
        for result in search_results:
            payload = result.payload
            base_score = result.score
            
            # Calculate boosted score based on content relevance
            boost_factor = 1.0
            
            # Boost based on content type relevance
            content_type = payload.get("content_type", "").lower()
            if any(term in content_type for term in ["tutorial", "guide", "example"]):
                boost_factor += 0.1
            
            # Boost if query terms appear in title or heading path
            title = payload.get("title", "").lower()
            heading_path = " ".join(payload.get("heading_path", [])).lower()
            query_terms = query.lower().split()
            
            for term in query_terms:
                if term in title:
                    boost_factor += 0.15
                if term in heading_path:
                    boost_factor += 0.1
            
            # Boost for code examples if query suggests implementation
            if payload.get("has_code", False) and any(term in query.lower() for term in 
                ["how to", "example", "implement", "create", "build", "code", "method"]):
                boost_factor += 0.1
            
            # Special boost for UI/overlay related content
            if any(ui_term in query.lower() for ui_term in ["ui", "menu", "screen", "overlay", "widget", "button", "navigation"]):
                content_lower = payload.get("content", "").lower()
                if any(overlay_term in content_lower for overlay_term in ["overlay", "widget", "menu", "screen", "ui"]):
                    boost_factor += 0.2
            
            boosted_score = base_score * boost_factor
            
            # Only include results that meet the final threshold
            if boosted_score >= min_score:
                enhanced_results.append({
                    "result": result,
                    "boosted_score": boosted_score
                })
        
        # Sort by boosted score and limit results
        enhanced_results.sort(key=lambda x: x["boosted_score"], reverse=True)
        enhanced_results = enhanced_results[:limit]
        
        # Format final results
        results = []
        for item in enhanced_results:
            result = item["result"]
            chunk_data = {
                "content": result.payload.get("content", ""),
                "title": result.payload.get("title", ""),
                "file_path": result.payload.get("file_path", ""),
                "section": result.payload.get("section", ""),
                "doc_url": result.payload.get("doc_url", ""),
                "heading_path": result.payload.get("heading_path", []),
                "has_code": result.payload.get("has_code", False),
                "content_type": result.payload.get("content_type", ""),
                "version": result.payload.get("version", ""),
                "similarity_score": round(item["boosted_score"], 3),
            }
            results.append(chunk_data)
        
        logger.info(f"Found {len(results)} relevant chunks for query: '{query}' (from {len(search_results)} initial results)")
        
        # If no results found, try a much broader search
        if not results:
            logger.info(f"No results with current threshold, trying broader search for: '{query}'")
            broader_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=5,
                score_threshold=0.1,  # Very low threshold
                with_payload=True,
            )
            
            if broader_results:
                results = []
                for result in broader_results:
                    chunk_data = {
                        "content": result.payload.get("content", ""),
                        "title": result.payload.get("title", ""),
                        "file_path": result.payload.get("file_path", ""),
                        "section": result.payload.get("section", ""),
                        "doc_url": result.payload.get("doc_url", ""),
                        "heading_path": result.payload.get("heading_path", []),
                        "has_code": result.payload.get("has_code", False),
                        "content_type": result.payload.get("content_type", ""),
                        "version": result.payload.get("version", ""),
                        "similarity_score": round(result.score, 3),
                    }
                    results.append(chunk_data)
                logger.info(f"Broader search found {len(results)} results")
        
        # If still no results, provide helpful message
        if not results:
            return [{
                "content": f"No relevant documentation found for query: '{query}'. Try using different terms or check if the documentation has been processed.",
                "title": "No Results",
                "file_path": "",
                "section": "search",
                "doc_url": "",
                "heading_path": [],
                "has_code": False,
                "content_type": "system",
                "version": version or "unknown",
                "similarity_score": 0.0,
            }]
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        return [{
            "content": f"Error searching knowledge base: {str(e)}",
            "title": "Search Error",
            "file_path": "",
            "section": "error",
            "doc_url": "",
            "heading_path": [],
            "has_code": False,
            "content_type": "error",
            "version": version or "unknown",
            "similarity_score": 0.0,
        }]


@mcp.custom_route("/health", methods=["GET"])
def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/", methods=["GET"])
def root_redirect(request: Request):
    """Redirect root to the web interface."""
    return FileResponse("web/index.html")

@mcp.custom_route("/docs", methods=["GET"])
def docs_redirect(request: Request):
    """Redirect /docs to the documentation page."""
    return FileResponse("web/docs.html")

@mcp.custom_route("/api/info", methods=["GET"])
def server_info(request: Request) -> JSONResponse:
    """Provide information about the MCP server and how to connect to it."""
    host = request.url.hostname or "localhost"
    port = request.url.port or 8000
    
    return JSONResponse({
        "server": "Flame Knowledge Base MCP Server",
        "transport": "streamable-http",
        "mcp_endpoint": f"http://{host}:{port}/mcp",
        "health_endpoint": f"http://{host}:{port}/health",
        "web_interface": f"http://{host}:{port}/",
        "documentation": f"http://{host}:{port}/docs",
        "connection_info": {
            "description": "This is a Model Context Protocol (MCP) server",
            "usage": "Connect using an MCP client to the /mcp endpoint",
            "tools": ["get_flame_knowledge"],
            "client_examples": {
                "fastmcp_client": f'Client("http://{host}:{port}/mcp")',
                "cursor_config": {
                    "mcpServers": {
                        "flame": {
                            "url": f"http://{host}:{port}/mcp",
                            "env": {}
                        }
                    }
                }
            }
        }
    })


if __name__ == "__main__":
    mcp.run()
