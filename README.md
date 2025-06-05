# Flame Documentation Processing Pipeline

This project processes Sphinx-generated Flame engine documentation, converting HTML to markdown, then chunking and embedding the content for storage in a Qdrant vector database.

> Contents under this repo is mostly (95%) writen by `claude-4-sonnet` and reviewed/revised by @dafashi-bing

## Overview

The pipeline consists of two main stages:
1. **HTML to Markdown Conversion**: Clean conversion from Sphinx HTML to readable markdown
2. **Chunking and Embedding**: Intelligent text chunking and vector embedding for knowledge base creation

## 🚀 Features

- **Smart Chunking**: Hybrid semantic + size-based splitting with overlap
- **Rich Metadata**: Version, file path, section, content type, heading hierarchy
- **Code Detection**: Identifies and preserves code examples with context
- **Error Recovery**: Graceful error handling with detailed error reporting
- **Resume Processing**: State persistence to resume interrupted runs
- **Rate Limiting**: Built-in rate limiting and retry logic for API calls
- **Comprehensive Logging**: Detailed logging with module identification

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd flame_mcp
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your actual configuration
   ```

4. **Prepare your documentation**:
   ```bash
   # Ensure your Sphinx docs are built to html
   # The processor expects files in _build/html/
   ```

5. **Convert Sphinx html doc into markdown**:

   ```bash
   # Convert with default directories (_build/html -> _build/markdown)
   python convert_sphinx_html_to_markdown.py
   
   # Or specify custom directories
   python convert_sphinx_html_to_markdown.py --source /path/to/html --output /path/to/markdown
   
   # See all options
   python convert_sphinx_html_to_markdown.py --help
   ```

## ⚙️ Configuration

### Environment Variables

```bash
# Azure OpenAI Configuration
OPENAI_API_KEY=your_azure_openai_api_key
OPENAI_API_VERSION=2024-02-01
OPENAI_API_BASE=https://your-resource.openai.azure.com/
OPENAI_MODEL_NAME=text-embedding-3-small

# Qdrant Configuration  
QDRANT_HOST=http://localhost:6333
QDRANT_PORT=6333
COLLECTION_NAME=flame_docs

# Rate Limiting Configuration (optional)
OPENAI_MAX_RETRIES=3        # Maximum retry attempts for API calls
OPENAI_BASE_DELAY=1.0       # Base delay in seconds for exponential backoff  
OPENAI_BATCH_DELAY=0.1      # Small delay between batch requests
```

### Logging Configuration

The system provides comprehensive logging with:
- **Module identification** in log messages
- **Automatic suppression** of noisy third-party logs that interfere with progress bars
- **Configurable log levels** via standard Python logging
- **File and console output** for debugging and monitoring

## 🏃‍♂️ Usage

### Basic Usage

```bash
# Process documentation with default settings
python process_flame_docs.py

# Specify version
python process_flame_docs.py --version 1.29.0

# Reset processing state (start fresh)
python process_flame_docs.py --reset
```

### Rate Limiting and Error Handling

The processor includes built-in rate limiting to handle API quotas:

- **Automatic retry** with exponential backoff for rate limit errors (429)
- **Configurable delays** between requests to avoid hitting limits
- **Graceful error handling** for non-rate-limit errors
- **Progress preservation** even when errors occur

Rate limiting parameters can be configured via environment variables:
- `OPENAI_MAX_RETRIES`: Number of retry attempts (default: 3)
- `OPENAI_BASE_DELAY`: Base delay for exponential backoff (default: 1.0s)
- `OPENAI_BATCH_DELAY`: Delay between batch requests (default: 0.1s)

## Features

### Intelligent Chunking
- **Semantic splitting**: Respects markdown headers and document structure
- **Size optimization**: Target ~900 tokens per chunk with 175 token overlap
- **Code preservation**: Keeps code blocks intact with surrounding context
- **Smart merging**: Combines small sections to avoid fragmentation

### Rich Metadata
Each chunk includes comprehensive metadata:
```json
{
  "version": "1.7.0",
  "file_path": "flame/game_widget.md",
  "section": "flame",
  "title": "Game Widget",
  "heading_path": ["Flame", "Game Widget", "Creating Widgets"],
  "content_type": "reference|tutorial|api|example",
  "has_code": true,
  "chunk_index": 0,
  "doc_url": "/flame/game_widget.html"
}
```

### Error Handling
- **Graceful failure**: Continues processing even if individual files fail
- **Detailed logging**: Comprehensive logs in `processing.log`
- **Error reporting**: Failed files tracked in `processing_errors.json`
- **Resume capability**: Can restart from partial completion

### Progress Tracking
- **Real-time progress**: Visual progress bar with tqdm
- **Processing stats**: Live updates on success/failure counts
- **State persistence**: Automatic state saving every 10 files

## Output Files

- `processing.log`: Detailed processing logs
- `processing_state.json`: Current processing state for resumability
- `processing_errors.json`: Error report for failed files (if any)

## Architecture

### Processing Pipeline
1. **File Discovery**: Recursively finds all `.md` files in `_build/markdown/`
2. **Content Analysis**: Extracts headers, detects code blocks, analyzes structure
3. **Chunking**: Creates semantic chunks with intelligent splitting
4. **Embedding**: Generates vectors using Azure OpenAI `text-embedding-3-small`
5. **Storage**: Stores in Qdrant with rich metadata for filtering

### Chunking Strategy
- **Primary**: Split by markdown headers (`#`, `##`, `###`)
- **Secondary**: Size-based splitting with paragraph/sentence boundaries
- **Overlap**: 175 tokens between adjacent chunks for context continuity
- **Merging**: Combines chunks smaller than 100 tokens

### Vector Storage
- **Collection**: Single collection with version-based filtering
- **Vectors**: 1536 dimensions (text-embedding-3-small)
- **Distance**: Cosine similarity
- **Indexing**: Optimized for fast metadata filtering

## Monitoring

Check processing status:
```bash
# View recent logs
tail -f processing.log

# Check processing state
cat processing_state.json

# Review any errors
cat processing_errors.json
```

## Integration

This pipeline prepares documentation for use with MCP (Model Context Protocol) tools. The resulting Qdrant collection can be queried with version filtering:

```python
# Example query with version filtering
results = qdrant_client.search(
    collection_name="flame_docs",
    query_vector=embedding,
    query_filter={"version": "1.7.0"},
    limit=10
)
```

## Performance

- **Throughput**: ~5-10 files per second (depending on file size and API latency)
- **Memory**: Minimal memory usage with streaming processing
- **Resumability**: Can handle interruptions without data loss
- **Batch Processing**: Efficient API usage with batch embedding creation

## Troubleshooting

### Common Issues

**"No markdown files found"**
- Ensure `_build/markdown/` directory exists
- Check that HTML to markdown conversion completed successfully

**API Authentication Errors**
- Verify `.env` file credentials
- Check Azure OpenAI resource status and quotas
- Confirm Qdrant instance accessibility

**Memory Issues**
- Processing uses streaming approach, but very large files may cause issues
- Consider splitting extremely large documents manually

**Interrupted Processing**
- Use `--reset` flag to start fresh if state file becomes corrupted
- Check `processing_errors.json` for specific file failures

### Debug Mode

Enable debug logging by modifying the script:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Documentation

See `doc/` directory for:
- `flame_docs_processing_plan.md`: Complete technical specification
- `todo.md`: Future enhancements and roadmap 

## 🔌 MCP Server

This project includes a Model Context Protocol (MCP) server that provides AI assistants with access to the Flame documentation knowledge base.

### Running the MCP Server

1. **Ensure your environment is configured**:
   ```bash
   # Make sure .env file is set up with all required variables
   cp env.example .env
   # Edit .env with your actual credentials
   ```

2. **Run the server**:
   ```bash
   python server.py
   ```

3. **The server will start and expose the following tools**:
   - `get_flame_knowledge`: Search the Flame documentation knowledge base

### MCP Tool Usage

#### `get_flame_knowledge`

Search the Flame documentation with semantic similarity.

**Parameters:**
- `query` (required): Search query related to Flame engine
- `version` (optional): Filter results by specific version (e.g., "1.29.0")
- `limit` (optional): Maximum number of results (default: 10)
- `min_score` (optional): Minimum similarity score threshold (default: 0.7)

**Example queries:**
- "How to create a Component in Flame?"
- "SpriteComponent animation methods"
- "Game loop and update lifecycle"
- "Collision detection with Hitbox"

**Returns:**
Each result includes:
```json
{
  "content": "The actual documentation content...",
  "title": "Page/Section Title",
  "file_path": "flame/components.md",
  "section": "flame",
  "doc_url": "/flame/components.html",
  "heading_path": ["Flame", "Components", "SpriteComponent"],
  "has_code": true,
  "content_type": "reference",
  "version": "1.29.0",
  "similarity_score": 0.85
}
```

### Integration with AI Assistants

The MCP server can be integrated with AI assistants that support the MCP protocol. When users ask questions about Flame engine development, the assistant can automatically query the knowledge base for the most relevant and up-to-date information.

**Benefits:**
- **Always current**: Uses the exact documentation you've processed
- **Version-specific**: Can filter by specific Flame versions
- **Semantic search**: Finds relevant content even with different wording
- **Rich context**: Includes metadata for better understanding

### Testing the Server

To test the server functionality:

```bash
# Test with mock data (doesn't require actual Qdrant/OpenAI)
python -c "
from unittest.mock import Mock, patch
from server import get_flame_knowledge

with patch('server.qdrant_client'), patch('server.openai_client'):
    results = get_flame_knowledge('test query')
    print(f'Server responds with: {len(results)} results')
"
```

## Thanks

This project is inspired by this [Godot RAG MCP](https://github.com/zivshek/rag-mcp)