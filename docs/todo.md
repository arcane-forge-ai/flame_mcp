# TODO - Flame Documentation Processing Pipeline

## Future Enhancements

### 1. Deduplication Strategy
**Priority**: Medium
**Description**: Implement deduplication for repeated content across Sphinx docs
**Options**:
- Hash-based exact duplicate removal
- Semantic similarity detection for near-duplicates
- Smart handling of common sections (navigation, footers)
**Rationale**: Sphinx docs often have repeated content that adds noise to vector search

### 2. Advanced Chunking Strategies
**Priority**: Low
**Description**: Explore div-based heading level detection
**Details**:
- Use div nesting depth to infer content hierarchy
- Look for semantic HTML elements (`<section>`, `<article>`)
- Identify content sections by CSS classes rather than just markdown headers
**Consideration**: Need to balance with existing `<h1>-<h6>` tag precedence

### 3. Code Example Extraction
**Priority**: Low  
**Description**: Evaluate separate handling of code examples
**Approach**:
- Extract code blocks as standalone searchable entities
- Maintain relationships between code and explanatory text
- Add specialized metadata (function names, imports, syntax)
**Use Case**: Enable code-specific queries like "show me sprite creation code"

### 4. Cross-Version Analysis
**Priority**: Medium
**Description**: Build tools to analyze documentation changes across versions
**Features**:
- Compare same sections across versions
- Identify deprecated features
- Track API evolution
**Implementation**: Query multiple version filters and analyze results

### 5. Quality Metrics Dashboard
**Priority**: Medium
**Description**: Create monitoring for chunk and embedding quality
**Metrics**:
- Chunk size distribution
- Content type distribution
- Embedding quality scores
- Retrieval accuracy metrics
- Search result relevance scoring

### 6. Enhanced Error Recovery
**Priority**: Low
**Description**: Implement smarter error recovery strategies
**Features**:
- Retry failed embeddings with different parameters
- Partial document processing (skip bad sections, not entire files)
- Automatic cleanup of incomplete processing states

### 7. Incremental Updates
**Priority**: High (for production)
**Description**: Support updating docs without full reprocessing
**Requirements**:
- Detect changed files since last processing
- Update only affected chunks in Qdrant
- Handle document deletions
- Version-aware incremental updates

### 8. Content Type Classification
**Priority**: Medium
**Description**: Improve automatic content type detection
**Approach**:
- ML-based classification of tutorial vs reference vs API docs
- File path pattern analysis
- Content structure analysis
**Benefit**: Better search filtering and relevance

### 9. Search Result Optimization
**Priority**: Medium
**Description**: Enhance retrieval quality
**Features**:
- Query expansion for domain-specific terms
- Context-aware result ranking
- Multi-modal search (text + code structure)
- User feedback integration

### 10. Documentation Coverage Analysis
**Priority**: Low
**Description**: Analyze completeness of documentation conversion
**Metrics**:
- Files processed vs total files
- Content sections successfully extracted
- Lost information during conversion
- Coverage gaps identification

## Implementation Notes

### Dependencies to Add Later
- `sentence-transformers` (for deduplication similarity)
- `scikit-learn` (for content classification)
- `nltk` or `spacy` (for advanced text processing)

### Infrastructure Considerations
- Consider moving to async processing for better performance
- Database migration strategy for schema changes
- Backup and recovery procedures for Qdrant collection
- Monitoring and alerting for production deployment

## Completed Items
- [ ] Basic HTML to Markdown conversion
- [ ] Chunking and embedding pipeline  
- [ ] Qdrant integration
- [ ] Version metadata strategy
- [ ] Error handling and reporting 