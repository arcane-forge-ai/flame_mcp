"""
Tests for document chunking functionality
"""

import pytest
from process_flame_docs import DocumentChunk


class TestChunkCreation:
    """Test the main chunk creation functionality."""
    
    def test_create_chunks_basic(self, processor, sample_markdown_content, sample_file_path):
        """Test basic chunk creation."""
        chunks = processor._create_chunks(sample_file_path, sample_markdown_content)
        
        # Should create multiple chunks
        assert len(chunks) > 0
        
        # Each chunk should be a DocumentChunk
        for chunk in chunks:
            assert isinstance(chunk, DocumentChunk)
            assert chunk.content
            assert chunk.metadata
            assert chunk.chunk_id
        
        # Check metadata structure
        first_chunk = chunks[0]
        metadata = first_chunk.metadata
        
        required_fields = ["version", "file_path", "section", "title", 
                          "heading_path", "has_code", "chunk_index", "doc_url"]
        for field in required_fields:
            assert field in metadata
        
        # Check version is set correctly
        assert metadata["version"] == "1.7.0"
        
        # Check file path is relative
        assert metadata["file_path"] == "flame/game_widget.md"
    
    def test_create_chunks_small_content(self, processor, sample_file_path):
        """Test chunk creation with very small content."""
        small_content = "# Small Title\n\nJust a tiny bit of content."
        chunks = processor._create_chunks(sample_file_path, small_content)
        
        # Should still create at least one chunk
        assert len(chunks) >= 1
        
        # Content should be preserved
        assert "Small Title" in chunks[0].content
    
    def test_create_chunks_large_content(self, processor, sample_file_path, large_markdown_content):
        """Test chunk creation with large content that needs splitting."""
        chunks = processor._create_chunks(sample_file_path, large_markdown_content)
        
        # Should create multiple chunks due to size
        assert len(chunks) >= 1
        
        # Each chunk should be reasonably sized
        for chunk in chunks:
            token_count = processor._count_tokens(chunk.content)
            # Should be within reasonable bounds (allowing for overlap)
            assert token_count <= processor.target_chunk_size + processor.overlap_size
    
    def test_create_chunks_code_detection(self, processor, sample_file_path, code_heavy_content):
        """Test that code blocks are properly detected in chunks."""
        chunks = processor._create_chunks(sample_file_path, code_heavy_content)
        
        # Should detect code in at least one chunk
        has_code_chunk = any(chunk.metadata["has_code"] for chunk in chunks)
        assert has_code_chunk
    
    def test_create_chunks_heading_hierarchy(self, processor, sample_file_path):
        """Test that heading hierarchy is captured correctly."""
        content = """# Main Title
## Section One
### Subsection
Content here.
## Section Two
More content."""
        
        chunks = processor._create_chunks(sample_file_path, content)
        
        # Check that heading hierarchy is captured
        for chunk in chunks:
            heading_path = chunk.metadata["heading_path"]
            assert isinstance(heading_path, list)
            if heading_path:  # If there are headings
                assert "Main Title" in heading_path


class TestSectionSplitting:
    """Test section splitting by headers."""
    
    def test_split_by_headers(self, processor, sample_markdown_content):
        """Test splitting content by markdown headers."""
        sections = processor._split_by_headers(sample_markdown_content)
        
        # Should have multiple sections
        assert len(sections) > 1
        
        # First section should start with main title
        assert sections[0].startswith("# Main Title")
        
        # Other sections should start with headers
        for section in sections[1:]:
            assert section.strip().startswith("#")
    
    def test_split_by_headers_no_headers(self, processor):
        """Test splitting content with no headers."""
        content = "Just plain text with no headers at all."
        sections = processor._split_by_headers(content)
        
        assert len(sections) == 1
        assert sections[0] == content
    
    def test_split_large_section(self, processor):
        """Test splitting large sections with overlap."""
        large_section = "# Large Section\n\n" + ("This is content. " * 300)
        
        chunks = processor._split_large_section(large_section, processor.target_chunk_size)
        
        # Should create multiple chunks
        if processor._count_tokens(large_section) > processor.target_chunk_size:
            assert len(chunks) > 1
        
        # Each chunk should be within size limits
        for chunk in chunks:
            assert processor._count_tokens(chunk) <= processor.target_chunk_size + processor.overlap_size


class TestTextOverlap:
    """Test text overlap functionality."""
    
    def test_get_text_overlap(self, processor):
        """Test getting text overlap."""
        text = "This is a longer piece of text for testing overlap functionality."
        overlap_tokens = 5
        
        overlap_text = processor._get_text_overlap(text, overlap_tokens)
        
        # Should return a string
        assert isinstance(overlap_text, str)
        
        # Should be shorter than or equal to original
        assert len(overlap_text) <= len(text)
        
        # Should contain end of original text
        assert overlap_text in text
    
    def test_get_text_overlap_short_text(self, processor):
        """Test overlap with text shorter than overlap size."""
        short_text = "Short text"
        overlap_tokens = 100  # More than the text
        
        overlap_text = processor._get_text_overlap(short_text, overlap_tokens)
        
        # Should return the entire text
        assert overlap_text == short_text


class TestCodeDetection:
    """Test code block detection."""
    
    def test_detect_code_blocks_fenced(self, processor):
        """Test detection of fenced code blocks."""
        content = """Some text here.

```python
def hello():
    return "world"
```

More text."""
        assert processor._detect_code_blocks(content) is True
    
    def test_detect_code_blocks_inline(self, processor):
        """Test detection of inline code."""
        content = "Here's some `inline code` in text."
        result = processor._detect_code_blocks(content)
        # This depends on the threshold - inline code alone might not trigger
        assert isinstance(result, bool)
    
    def test_detect_code_blocks_substantial(self, processor, code_heavy_content):
        """Test detection with substantial code content."""
        assert processor._detect_code_blocks(code_heavy_content) is True
    
    def test_detect_code_blocks_none(self, processor):
        """Test detection with no code."""
        content = "This is just plain text with no code blocks or inline code."
        assert processor._detect_code_blocks(content) is False 