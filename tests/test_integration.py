"""
Integration tests for the complete processing pipeline
"""

import pytest
from pathlib import Path
from unittest.mock import Mock


class TestFileProcessing:
    """Integration tests for file processing."""
    
    def test_process_file_complete_flow(self, processor, tmp_path):
        """Test complete file processing flow with mocked dependencies."""
        # Create a temporary markdown file within the processor's source directory
        test_file = processor.source_dir / "test.md"
        test_content = """# Test Document

This is a test document with some content.

## Section 1

Content in section 1 with `code`.

```python
print("Hello")
```

More content after the code block.
"""
        test_file.write_text(test_content)
        
        # Mock the embedding response
        mock_response = Mock()
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response.data = [mock_embedding]
        processor.openai_client.embeddings.create.return_value = mock_response
        
        # Process the file
        result = processor._process_file(test_file)
        
        # Should succeed
        assert result is True
        
        # Should be marked as processed
        assert str(test_file) in processor.processed_files
        
        # Should have created embeddings and stored in Qdrant
        processor.openai_client.embeddings.create.assert_called()
        processor.qdrant_client.upsert.assert_called()
    
    def test_process_file_with_errors(self, processor, tmp_path):
        """Test file processing with various error conditions."""
        # Create test file within processor's source directory
        test_file = processor.source_dir / "error_test.md"
        test_file.write_text("# Test\nContent here.")
        
        # Simulate embedding API error
        processor.openai_client.embeddings.create.side_effect = Exception("API Error")
        
        # Process should fail gracefully
        result = processor._process_file(test_file)
        
        assert result is False
        assert len(processor.errors) > 0
        assert processor.errors[-1]["file"] == str(test_file)
    
    def test_process_file_already_processed(self, processor, tmp_path):
        """Test that already processed files are skipped."""
        test_file = processor.source_dir / "already_processed.md"
        test_file.write_text("# Test\nContent here.")
        
        # Mark file as already processed
        processor.processed_files.add(str(test_file))
        
        result = processor._process_file(test_file)
        
        # Should succeed but skip processing
        assert result is True
        
        # Should not call embedding API
        processor.openai_client.embeddings.create.assert_not_called()
    
    def test_process_empty_file(self, processor, tmp_path):
        """Test processing empty files."""
        test_file = processor.source_dir / "empty.md"
        test_file.write_text("")
        
        result = processor._process_file(test_file)
        
        # Should handle gracefully
        assert result is True
        
        # Should not create embeddings for empty content
        processor.openai_client.embeddings.create.assert_not_called()


class TestBatchProcessing:
    """Test batch processing of multiple files."""
    
    def test_process_multiple_files_success(self, processor, tmp_path):
        """Test processing multiple files successfully."""
        # Create multiple test files within the processor's source directory
        files = []
        for i in range(3):
            test_file = processor.source_dir / f"test_{i}.md"
            test_file.write_text(f"# Document {i}\n\nContent for document {i}.")
            files.append(test_file)
        
        # Mock embedding responses
        mock_response = Mock()
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response.data = [mock_embedding]
        processor.openai_client.embeddings.create.return_value = mock_response
        
        # Process all files
        processor.process_all_files()
        
        # All files should be processed
        assert len(processor.processed_files) == 3
        
        # Should have called embedding API multiple times
        assert processor.openai_client.embeddings.create.call_count >= 3
    
    def test_process_files_with_mixed_results(self, processor, tmp_path):
        """Test processing files with some successes and some failures."""
        # Create test files within processor's source directory
        good_file = processor.source_dir / "good.md"
        good_file.write_text("# Good Document\n\nThis will process fine.")
        
        bad_file = processor.source_dir / "bad.md"
        bad_file.write_text("# Bad Document\n\nThis will cause an error.")
        
        # Mock embedding to fail for specific content
        def mock_embedding_side_effect(*args, **kwargs):
            if "Bad Document" in str(kwargs.get('input', [])):
                raise Exception("Simulated API Error")
            
            mock_response = Mock()
            mock_embedding = Mock()
            mock_embedding.embedding = [0.1] * 1536
            mock_response.data = [mock_embedding]
            return mock_response
        
        processor.openai_client.embeddings.create.side_effect = mock_embedding_side_effect
        
        processor.process_all_files()
        
        # Should have one success and one failure
        assert len(processor.processed_files) == 1
        assert len(processor.errors) == 1


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_full_pipeline_workflow(self, processor, tmp_path):
        """Test the complete pipeline from file discovery to storage."""
        # Create a realistic document structure within the processor's source directory
        (processor.source_dir / "flame").mkdir()
        (processor.source_dir / "tutorials").mkdir()
        
        # Create various types of documents
        flame_doc = processor.source_dir / "flame" / "components.md"
        flame_doc.write_text("""# Components

Components are the building blocks of Flame games.

## Component Lifecycle

```dart
class MyComponent extends Component {
  @override
  Future<void> onLoad() async {
    // Initialization code
  }
}
```

This shows the basic component structure.
""")
        
        tutorial_doc = processor.source_dir / "tutorials" / "getting_started.md"
        tutorial_doc.write_text("""# Getting Started

This tutorial will help you get started with Flame.

## Installation

Add Flame to your pubspec.yaml:

```yaml
dependencies:
  flame: ^1.7.0
```

Then import it in your code.
""")
        
        # Mock all external dependencies
        mock_response = Mock()
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response.data = [mock_embedding]
        processor.openai_client.embeddings.create.return_value = mock_response
        
        # Run the complete pipeline
        processor.process_all_files()
        
        # Verify results
        assert len(processor.processed_files) == 2
        assert processor.chunks_created > 0
        
        # Verify different document types were processed
        processed_paths = list(processor.processed_files)
        assert any("flame" in path for path in processed_paths)
        assert any("tutorials" in path for path in processed_paths)
        
        # Verify embeddings were created and stored
        assert processor.openai_client.embeddings.create.call_count >= 2
        assert processor.qdrant_client.upsert.call_count >= 2
    
    def test_resumable_processing(self, processor, tmp_path):
        """Test that processing can be resumed after interruption."""
        # Create test files within processor's source directory
        file1 = processor.source_dir / "file1.md"
        file1.write_text("# Document 1\nContent here.")
        
        file2 = processor.source_dir / "file2.md"
        file2.write_text("# Document 2\nMore content.")
        
        # Use the processor's temporary state file
        processor.processed_files.add(str(file1))
        processor.chunks_created = 5
        processor._save_state()
        
        # Mock embeddings
        mock_response = Mock()
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response.data = [mock_embedding]
        processor.openai_client.embeddings.create.return_value = mock_response
        
        # Create new processor instance (simulating restart)
        from process_flame_docs import FlameDocsProcessor
        from unittest.mock import patch
        
        with patch('process_flame_docs.AzureOpenAI'), \
             patch('process_flame_docs.QdrantClient'):
            new_processor = FlameDocsProcessor(version="1.7.0")
            # Set the paths before loading state
            new_processor.source_dir = processor.source_dir
            new_processor.state_file = processor.state_file
            new_processor.error_file = processor.error_file
            new_processor.openai_client = processor.openai_client
            new_processor.qdrant_client = processor.qdrant_client
            
            # Manually reload state from the correct file
            new_processor.processed_files = set()
            new_processor.chunks_created = 0
            new_processor._load_state()
            
            # Should load previous state
            assert len(new_processor.processed_files) == 1
            assert new_processor.chunks_created == 5
            
            # Process remaining files
            new_processor.process_all_files()
            
            # Should process only the unprocessed file
            assert len(new_processor.processed_files) == 2 