"""
Shared pytest fixtures for Flame Documentation Processing Pipeline tests
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from process_flame_docs import FlameDocsProcessor, DocumentChunk


@pytest.fixture
def mock_openai_client():
    """Mock Azure OpenAI client with typical responses."""
    with patch('process_flame_docs.AzureOpenAI') as mock_client:
        # Setup typical embedding response
        mock_response = Mock()
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
        mock_response.data = [mock_embedding]
        
        mock_instance = Mock()
        mock_instance.embeddings.create.return_value = mock_response
        mock_client.return_value = mock_instance
        
        yield mock_instance


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client."""
    with patch('process_flame_docs.QdrantClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def processor(mock_openai_client, mock_qdrant_client, tmp_path):
    """Create a processor instance with mocked clients."""
    processor = FlameDocsProcessor(version="1.7.0")
    processor.source_dir = tmp_path / "test_source"
    processor.source_dir.mkdir(exist_ok=True)
    processor.openai_client = mock_openai_client
    processor.qdrant_client = mock_qdrant_client
    
    # Reset state for test isolation
    processor.processed_files = set()
    processor.chunks_created = 0
    processor.errors = []
    
    # Use temporary state file for each test
    processor.state_file = tmp_path / "test_state.json"
    processor.error_file = tmp_path / "test_errors.json"
    
    return processor


@pytest.fixture
def sample_markdown_content():
    """Sample markdown content for testing."""
    return """# Main Title

This is the introduction paragraph with some text.

## Section 1

Here's some content in section 1 with `inline code` and regular text.

```python
def example_function():
    return "Hello World"
```

More text after code block.

## Section 2

### Subsection 2.1

Another paragraph with more content. This paragraph is longer to test
the chunking behavior when we have substantial content that might need
to be split across multiple chunks.

- List item 1
- List item 2
- List item 3

## Section 3

Final section with minimal content.
"""


@pytest.fixture
def sample_file_path(processor):
    """Sample file path for testing."""
    # Create the flame directory and file within the processor's source directory
    flame_dir = processor.source_dir / "flame"
    flame_dir.mkdir(exist_ok=True)
    
    file_path = flame_dir / "game_widget.md"
    file_path.write_text("# Sample Content\n\nThis is test content.")
    
    return file_path


@pytest.fixture
def large_markdown_content():
    """Large markdown content for testing chunking behavior."""
    return "# Large Document\n\n" + ("This is a long paragraph with substantial content. " * 200)


@pytest.fixture
def code_heavy_content():
    """Markdown content with significant code blocks."""
    return """# Code Example

Here's a Python function:

```python
def process_data(data):
    result = []
    for item in data:
        result.append(item.upper())
    return result
```

And here's another example:

```dart
class Player extends SpriteComponent {
  @override
  Future<void> onLoad() async {
    sprite = await Sprite.load('player.png');
    size = Vector2(32, 32);
  }
}
```

This content has substantial code blocks."""


@pytest.fixture
def sample_chunks():
    """Sample DocumentChunk objects for testing."""
    return [
        DocumentChunk(
            content="Test content 1", 
            metadata={"version": "1.7.0", "test": "meta1"}, 
            chunk_id="id1"
        ),
        DocumentChunk(
            content="Test content 2", 
            metadata={"version": "1.7.0", "test": "meta2"}, 
            chunk_id="id2"
        )
    ]


@pytest.fixture
def sample_embeddings():
    """Sample embedding vectors for testing."""
    return [
        [0.1, 0.2, 0.3] * 512,  # 1536 dimensions
        [0.4, 0.5, 0.6] * 512   # 1536 dimensions
    ] 