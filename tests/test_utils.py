"""
Tests for utility functions and state management
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch


class TestTokenCounting:
    """Test token counting functionality."""
    
    def test_count_tokens_short_text(self, processor):
        """Test token counting with short text."""
        short_text = "Hello world"
        count = processor._count_tokens(short_text)
        assert count > 0
        assert count < 10
    
    def test_count_tokens_empty_text(self, processor):
        """Test token counting with empty text."""
        assert processor._count_tokens("") == 0
    
    def test_count_tokens_long_text(self, processor):
        """Test token counting with longer text."""
        short_text = "Hello world"
        long_text = "This is a much longer piece of text " * 10
        
        short_count = processor._count_tokens(short_text)
        long_count = processor._count_tokens(long_text)
        
        assert long_count > short_count
    
    def test_count_tokens_with_code(self, processor):
        """Test token counting with code blocks."""
        code_text = """
```python
def hello_world():
    print("Hello, World!")
    return True
```
"""
        count = processor._count_tokens(code_text)
        assert count > 0
    
    def test_count_tokens_with_markdown(self, processor):
        """Test token counting with markdown formatting."""
        markdown_text = """
# Header
## Subheader
- List item 1
- List item 2
**Bold text** and *italic text*
[Link](https://example.com)
"""
        count = processor._count_tokens(markdown_text)
        assert count > 0


class TestStateManagement:
    """Test state saving and loading."""
    
    def test_save_and_load_state(self, processor, tmp_path):
        """Test state persistence."""
        # Use temporary files for testing
        processor.state_file = tmp_path / "test_state.json"
        
        # Set some state
        processor.processed_files.add("file1.md")
        processor.processed_files.add("file2.md")
        processor.chunks_created = 42
        
        # Save state
        processor._save_state()
        
        # Verify file was created
        assert processor.state_file.exists()
        
        # Create new processor instance and load state
        with patch('process_flame_docs.AzureOpenAI'), \
             patch('process_flame_docs.QdrantClient'):
            from process_flame_docs import FlameDocsProcessor
            new_processor = FlameDocsProcessor(version="1.7.0")
            new_processor.state_file = processor.state_file
            new_processor._load_state()
        
        # State should be restored
        assert len(new_processor.processed_files) == 2
        assert "file1.md" in new_processor.processed_files
        assert "file2.md" in new_processor.processed_files
        assert new_processor.chunks_created == 42
    
    def test_save_state_creates_valid_json(self, processor, tmp_path):
        """Test that saved state is valid JSON."""
        processor.state_file = tmp_path / "test_state.json"
        processor.processed_files.add("test.md")
        processor.chunks_created = 10
        
        processor._save_state()
        
        # Should be able to load as JSON
        with open(processor.state_file, 'r') as f:
            state = json.load(f)
        
        assert "processed_files" in state
        assert "chunks_created" in state
        assert "last_updated" in state
        assert state["chunks_created"] == 10
    
    def test_load_state_missing_file(self, processor, tmp_path):
        """Test loading state when file doesn't exist."""
        processor.state_file = tmp_path / "nonexistent.json"
        
        # Should not raise an error
        processor._load_state()
        
        # Should have default empty state
        assert len(processor.processed_files) == 0
        assert processor.chunks_created == 0
    
    def test_load_state_corrupted_file(self, processor, tmp_path):
        """Test loading state with corrupted JSON file."""
        processor.state_file = tmp_path / "corrupted.json"
        
        # Create corrupted JSON file
        with open(processor.state_file, 'w') as f:
            f.write("invalid json content {")
        
        # Should handle gracefully
        processor._load_state()
        
        # Should have default state
        assert len(processor.processed_files) == 0


class TestErrorHandling:
    """Test error handling and reporting."""
    
    def test_save_errors(self, processor, tmp_path):
        """Test error reporting functionality."""
        processor.error_file = tmp_path / "test_errors.json"
        
        # Add some errors
        processor.errors = [
            {
                "file": "test1.md",
                "error": "Test error 1",
                "timestamp": "2024-01-01T00:00:00"
            },
            {
                "file": "test2.md", 
                "error": "Test error 2",
                "timestamp": "2024-01-01T00:01:00"
            }
        ]
        
        processor._save_errors()
        
        # Verify file was created
        assert processor.error_file.exists()
        
        # Verify content
        with open(processor.error_file, 'r') as f:
            errors = json.load(f)
        
        assert len(errors) == 2
        assert errors[0]["file"] == "test1.md"
        assert errors[1]["file"] == "test2.md"
    
    def test_save_errors_empty_list(self, processor, tmp_path):
        """Test saving empty error list."""
        processor.error_file = tmp_path / "empty_errors.json"
        processor.errors = []
        
        processor._save_errors()
        
        # Should not create file for empty errors
        assert not processor.error_file.exists()


class TestConfigurationParameters:
    """Test chunking configuration parameters."""
    
    def test_default_chunking_parameters(self, processor):
        """Test that default chunking parameters are reasonable."""
        assert processor.target_chunk_size == 900
        assert processor.overlap_size == 175
        assert processor.min_chunk_size == 100
        
        # Overlap should be smaller than target
        assert processor.overlap_size < processor.target_chunk_size
        
        # Min size should be smaller than target
        assert processor.min_chunk_size < processor.target_chunk_size
    
    def test_version_setting(self, processor):
        """Test that version is set correctly."""
        assert processor.version == "1.7.0"
    
    def test_source_directory_setting(self, processor):
        """Test that source directory is set."""
        assert processor.source_dir is not None
        assert isinstance(processor.source_dir, Path) 