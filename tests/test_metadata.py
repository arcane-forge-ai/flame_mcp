"""
Tests for metadata extraction and processing
"""

import pytest
from pathlib import Path


class TestMetadataExtraction:
    """Test metadata extraction from file paths."""
    
    def test_extract_metadata_from_path_flame_section(self, processor):
        """Test metadata extraction for flame section files."""
        file_path = Path("_build/markdown/flame/game_widget.md")
        processor.source_dir = Path("_build/markdown")
        
        metadata = processor._extract_metadata_from_path(file_path)
        
        assert metadata["version"] == "1.7.0"
        assert metadata["file_path"] == "flame/game_widget.md"
        assert metadata["section"] == "flame"
        assert metadata["content_type"] == "reference"
    
    def test_extract_metadata_from_path_tutorial(self, processor):
        """Test metadata extraction for tutorial files."""
        file_path = Path("_build/markdown/tutorials/platformer/step_1.md")
        processor.source_dir = Path("_build/markdown")
        
        metadata = processor._extract_metadata_from_path(file_path)
        
        assert metadata["section"] == "tutorials"
        assert metadata["content_type"] == "tutorial"
        assert metadata["version"] == "1.7.0"
        assert "tutorials" in metadata["file_path"]
    
    def test_extract_metadata_from_path_api(self, processor):
        """Test metadata extraction for API reference files."""
        file_path = Path("_build/markdown/api/components.md")
        processor.source_dir = Path("_build/markdown")
        
        metadata = processor._extract_metadata_from_path(file_path)
        
        assert metadata["content_type"] == "api"
        assert metadata["section"] == "api"
    
    def test_extract_metadata_from_path_bridge_packages(self, processor):
        """Test metadata extraction for bridge package files."""
        file_path = Path("_build/markdown/bridge_packages/flame_audio/audio.md")
        processor.source_dir = Path("_build/markdown")
        
        metadata = processor._extract_metadata_from_path(file_path)
        
        assert metadata["section"] == "bridge_packages"
        assert metadata["content_type"] == "reference"
    
    def test_extract_metadata_from_path_example(self, processor):
        """Test metadata extraction for example files."""
        file_path = Path("_build/markdown/examples/simple_game.md")
        processor.source_dir = Path("_build/markdown")
        
        metadata = processor._extract_metadata_from_path(file_path)
        
        assert metadata["content_type"] == "example"
        assert metadata["section"] == "examples"
    
    def test_extract_metadata_nested_paths(self, processor):
        """Test metadata extraction with deeply nested paths."""
        file_path = Path("_build/markdown/other_modules/jenny/language/commands/character.md")
        processor.source_dir = Path("_build/markdown")
        
        metadata = processor._extract_metadata_from_path(file_path)
        
        assert metadata["section"] == "other_modules"
        assert "jenny/language/commands/character.md" in metadata["file_path"]


class TestHeadingExtraction:
    """Test heading hierarchy extraction."""
    
    def test_extract_heading_hierarchy_simple(self, processor):
        """Test heading extraction with simple hierarchy."""
        content = """# Main Title
## Section 1
### Subsection 1.1
## Section 2
"""
        headings = processor._extract_heading_hierarchy(content)
        expected = ["Main Title", "Section 1", "Subsection 1.1", "Section 2"]
        assert headings == expected
    
    def test_extract_heading_hierarchy_nested(self, processor):
        """Test heading extraction with proper nesting."""
        content = """# Title
## Section A
### Subsection A.1
#### Deep Section
### Subsection A.2
## Section B
"""
        headings = processor._extract_heading_hierarchy(content)
        # Should maintain proper hierarchy
        assert "Title" in headings
        assert "Section A" in headings
        assert "Section B" in headings
    
    def test_extract_heading_hierarchy_empty(self, processor):
        """Test heading extraction with no headings."""
        content = "Just plain text with no headings."
        headings = processor._extract_heading_hierarchy(content)
        assert headings == []
    
    def test_extract_heading_hierarchy_with_special_chars(self, processor):
        """Test heading extraction with special characters."""
        content = """# Main Title with `code`
## Section with **bold** text
### Sub-section with links [link](url)
"""
        headings = processor._extract_heading_hierarchy(content)
        
        assert "Main Title with `code`" in headings
        assert "Section with **bold** text" in headings
        assert "Sub-section with links [link](url)" in headings
    
    def test_extract_heading_hierarchy_malformed(self, processor):
        """Test heading extraction with malformed headers."""
        content = """# Valid Header
##Missing space
### Valid Sub-header
# Another Valid Header
"""
        headings = processor._extract_heading_hierarchy(content)
        
        # Should handle malformed headers gracefully
        assert "Valid Header" in headings
        assert "Valid Sub-header" in headings
        assert "Another Valid Header" in headings 