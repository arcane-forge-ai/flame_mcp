# Flame Documentation Processing Pipeline

## Overview
Convert Sphinx-generated Flame engine documentation from HTML to markdown, then chunk and embed for storage in Qdrant vector database. This will serve as a knowledge base for AI systems via MCP (Model Context Protocol) tools.

## Pipeline Stages

### 1. HTML to Markdown Conversion

**Objective**: Convert Sphinx HTML docs to clean markdown files

**Key Decisions**:
- Target main content only: `<div class="document" role="main">` (excludes navigation, sidebars)
- Use `markdownify` + `BeautifulSoup` for parsing
- Preserve directory structure from `_build/html` to `_build/markdown`
- Fallback to full HTML conversion if main content div not found

**Implementation**: 
- Function: `convert_html_to_markdown()`
- Dependencies: `markdownify`, `beautifulsoup4`

### 2. Chunking and Embedding

**Objective**: Break markdown into semantic chunks and create embeddings for vector search

#### Chunking Strategy
**Primary**: Semantic sections (markdown headers `#`, `##`, `###`)
- Preserve logical document structure
- Keep related subsections together when short
- Handle code blocks as complete units

**Secondary**: Size-based splitting
- **Target chunk size**: 800-1000 tokens
- **Overlap size**: 150-200 tokens  
- **Minimum chunk size**: Merge chunks < 100 tokens
- Smart splitting respecting sentence/code boundaries

**Code Examples**: Keep with surrounding context (not separate entities)
- Rationale: Game engine docs need context for complex examples
- Flag code-containing chunks in metadata

#### Embedding Configuration
- **Model**: `text-embedding-3-small` via Azure OpenAI
- **Preprocessing**: Normalize text, handle code blocks appropriately
- **Processing**: Batch embeddings for efficiency

### 3. Version Handling

**Strategy**: Single collection with version metadata (not separate collections)

**Rationale**:
- Simpler infrastructure management
- Enables cross-version queries
- Efficient filtering with Qdrant indexes
- Easier for MCP tool integration

### 4. Qdrant Storage

#### Collection Configuration
- **Vector dimensions**: 1536 (text-embedding-3-small)
- **Distance metric**: Cosine
- **HNSW parameters**: m=16, ef_construct=200
- **Collection name**: `flame_docs`

#### Metadata Schema
```json
{
  "version": "1.7.0",
  "file_path": "flame/game_widget.md",
  "section": "flame",
  "title": "Game Widget", 
  "heading_path": ["Flame", "Game Widget", "Creating Widgets"],
  "content_type": "reference|tutorial|api|example",
  "has_code": boolean,
  "chunk_index": 0,
  "doc_url": "original sphinx URL for reference"
}
```

## Data Pipeline Architecture

### Processing Strategy
- **File Processing**: Batch all (process files as discovered)
- **Progress Tracking**: Resume capability with state file
- **Memory Management**: Stream processing (one file at a time) 
- **Error Handling**: Skip failed files, continue processing

### Error Handling Details
- Skip failed files with detailed logging
- Create error report file (separate from logs)
- Continue processing to maximize successful completion
- Detailed error reporting for post-processing review

### Progress Reporting
- Real-time progress with tqdm
- Logging for processing status
- State tracking for resume capability

## Environment Configuration

```env
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=...
QDRANT_HOST=...
QDRANT_API_KEY=...
COLLECTION_NAME=flame_docs
```

## Implementation Approach
- **Type**: Standalone script
- **Dependencies**: markdownify, beautifulsoup4, openai, qdrant-client, tqdm
- **Resumability**: State file to track processed files
- **Output**: Processed markdown files + populated Qdrant collection

## Future Integration
- **MCP Tool**: Will query collection with version filtering
- **Query Pattern**: `{"version": "1.7.0"}` metadata filter
- **Default**: Use "latest" version when not specified

## Quality Assurance Plan
- Test query set for typical Flame questions
- Quality metrics for chunk validation
- Retrieval testing with sample queries
- Embedding quality verification 