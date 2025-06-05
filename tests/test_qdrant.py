"""
Tests for Qdrant storage functionality
"""

import pytest
from unittest.mock import Mock
from process_flame_docs import DocumentChunk


class TestQdrantStorage:
    """Test Qdrant storage functionality."""
    
    def test_store_in_qdrant_success(self, processor, sample_chunks, sample_embeddings):
        """Test successful storage in Qdrant."""
        processor.collection_name = "test_collection"
        
        processor._store_in_qdrant(sample_chunks, sample_embeddings)
        
        # Verify upsert was called
        processor.qdrant_client.upsert.assert_called_once()
        call_args = processor.qdrant_client.upsert.call_args
        
        assert call_args[1]['collection_name'] == "test_collection"
        points = call_args[1]['points']
        assert len(points) == 2
        
        # Verify point structure
        for point in points:
            assert hasattr(point, 'id')
            assert hasattr(point, 'vector')
            assert hasattr(point, 'payload')
    
    def test_store_in_qdrant_mismatch(self, processor, sample_chunks):
        """Test error when chunks and embeddings don't match."""
        # Too many embeddings
        bad_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        
        with pytest.raises(ValueError, match="Number of chunks and embeddings must match"):
            processor._store_in_qdrant(sample_chunks, bad_embeddings)
    
    def test_store_in_qdrant_empty_lists(self, processor):
        """Test storing empty lists."""
        processor._store_in_qdrant([], [])
        
        # Should still call upsert with empty points
        processor.qdrant_client.upsert.assert_called_once()
        call_args = processor.qdrant_client.upsert.call_args
        points = call_args[1]['points']
        assert len(points) == 0
    
    def test_store_in_qdrant_api_error(self, processor, sample_chunks, sample_embeddings):
        """Test handling of Qdrant API errors."""
        processor.qdrant_client.upsert.side_effect = Exception("Qdrant API Error")
        
        with pytest.raises(Exception, match="Qdrant API Error"):
            processor._store_in_qdrant(sample_chunks, sample_embeddings)
    
    def test_store_in_qdrant_metadata_preservation(self, processor, sample_embeddings):
        """Test that metadata is properly preserved in storage."""
        # Create chunks with rich metadata
        chunks = [
            DocumentChunk(
                content="Test content 1",
                metadata={
                    "version": "1.7.0",
                    "file_path": "flame/test.md",
                    "section": "flame",
                    "title": "Test Document",
                    "has_code": True,
                    "chunk_index": 0
                },
                chunk_id="test_id_1"
            )
        ]
        
        processor._store_in_qdrant(chunks, [sample_embeddings[0]])
        
        # Verify metadata was included in payload
        call_args = processor.qdrant_client.upsert.call_args
        points = call_args[1]['points']
        
        payload = points[0].payload
        assert payload["version"] == "1.7.0"
        assert payload["file_path"] == "flame/test.md"
        assert payload["has_code"] is True


class TestCollectionManagement:
    """Test Qdrant collection management."""
    
    def test_ensure_collection_exists_already_exists(self, processor):
        """Test when collection already exists."""
        # Reset the mock call count since it was called during initialization
        processor.qdrant_client.get_collection.reset_mock()
        
        # Mock successful get_collection call
        processor.qdrant_client.get_collection.return_value = Mock()
        
        processor._ensure_collection_exists()
        
        # Should check for existing collection
        processor.qdrant_client.get_collection.assert_called_once_with(processor.collection_name)
        
        # Should not create new collection
        processor.qdrant_client.create_collection.assert_not_called()
    
    def test_ensure_collection_exists_create_new(self, processor):
        """Test creating new collection when it doesn't exist."""
        # Reset the mock call count since it was called during initialization
        processor.qdrant_client.get_collection.reset_mock()
        processor.qdrant_client.create_collection.reset_mock()
        
        # Mock get_collection to raise exception (collection doesn't exist)
        processor.qdrant_client.get_collection.side_effect = Exception("Collection not found")
        
        processor._ensure_collection_exists()
        
        # Should try to get existing collection
        processor.qdrant_client.get_collection.assert_called_once_with(processor.collection_name)
        
        # Should create new collection
        processor.qdrant_client.create_collection.assert_called_once()
        call_args = processor.qdrant_client.create_collection.call_args
        
        # Verify collection parameters
        assert call_args[1]['collection_name'] == processor.collection_name
        assert 'vectors_config' in call_args[1]
        assert 'hnsw_config' in call_args[1]
    
    def test_collection_vector_configuration(self, processor):
        """Test that collection is created with correct vector configuration."""
        # Reset the mock call count since it was called during initialization
        processor.qdrant_client.get_collection.reset_mock()
        processor.qdrant_client.create_collection.reset_mock()
        
        processor.qdrant_client.get_collection.side_effect = Exception("Collection not found")
        
        processor._ensure_collection_exists()
        
        call_args = processor.qdrant_client.create_collection.call_args
        vectors_config = call_args[1]['vectors_config']
        
        # Should be configured for text-embedding-3-small
        assert vectors_config.size == 1536
        # Should use cosine distance
        assert hasattr(vectors_config, 'distance')
    
    def test_collection_name_from_env(self, processor):
        """Test that collection name comes from configuration."""
        # Collection name should be set from environment or default
        assert processor.collection_name is not None
        assert isinstance(processor.collection_name, str) 