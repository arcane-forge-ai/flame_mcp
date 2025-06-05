"""
Tests for embedding creation and management
"""

import pytest
import time
from unittest.mock import Mock, patch
from process_flame_docs import DocumentChunk


class TestEmbeddingCreation:
    """Test embedding creation functionality."""
    
    def test_create_embeddings_success(self, processor, sample_chunks):
        """Test successful embedding creation."""
        # Setup mock response with correct number of embeddings
        mock_response = Mock()
        mock_embedding1 = Mock()
        mock_embedding1.embedding = [0.1] * 1536
        mock_embedding2 = Mock()
        mock_embedding2.embedding = [0.2] * 1536
        mock_response.data = [mock_embedding1, mock_embedding2]
        processor.openai_client.embeddings.create.return_value = mock_response
        
        embeddings = processor._create_embeddings(sample_chunks)
        
        assert len(embeddings) == 2
        assert len(embeddings[0]) == 1536  # text-embedding-3-small dimension
        assert len(embeddings[1]) == 1536
        
        # Verify API was called correctly
        processor.openai_client.embeddings.create.assert_called_once()
        call_args = processor.openai_client.embeddings.create.call_args
        
        # Check that texts were passed correctly
        texts = call_args[1]['input']
        assert len(texts) == 2
        assert texts[0] == "Test content 1"
        assert texts[1] == "Test content 2"
    
    def test_create_embeddings_empty_chunks(self, processor):
        """Test handling of empty chunk list."""
        embeddings = processor._create_embeddings([])
        
        assert embeddings == []
        # API should not be called for empty input
        processor.openai_client.embeddings.create.assert_not_called()
    
    def test_create_embeddings_single_chunk(self, processor):
        """Test embedding creation for single chunk."""
        chunk = DocumentChunk(
            content="Single test content",
            metadata={"test": "single"},
            chunk_id="single_id"
        )
        
        embeddings = processor._create_embeddings([chunk])
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1536
    
    def test_create_embeddings_api_error(self, processor, sample_chunks):
        """Test handling of non-rate-limit API errors."""
        # Mock API to raise a non-rate-limit error
        processor.openai_client.embeddings.create.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            processor._create_embeddings(sample_chunks)
    
    def test_create_embeddings_rate_limit_retry(self, processor, sample_chunks):
        """Test retry logic for rate limit errors."""
        # Set shorter delays for testing
        processor.max_retries = 2  
        processor.base_delay = 0.01  # Very short delay for testing
        
        # Mock API to fail first time with rate limit, then succeed
        mock_responses = [
            Exception("HTTP Error 429: Too Many Requests"),
            Mock()
        ]
        
        # Setup successful response for second attempt
        mock_response = Mock()
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response.data = [mock_embedding] * len(sample_chunks)
        mock_responses[1] = mock_response
        
        processor.openai_client.embeddings.create.side_effect = mock_responses
        
        start_time = time.time()
        embeddings = processor._create_embeddings(sample_chunks)
        end_time = time.time()
        
        # Should have succeeded after retry
        assert len(embeddings) == len(sample_chunks)
        
        # Should have taken some time due to delay
        assert end_time - start_time >= processor.base_delay
        
        # Should have been called twice
        assert processor.openai_client.embeddings.create.call_count == 2
    
    def test_create_embeddings_rate_limit_exhausted(self, processor, sample_chunks):
        """Test failure after exhausting retries for rate limits."""
        # Set minimal retries for testing
        processor.max_retries = 2
        processor.base_delay = 0.01
        
        # Mock API to always fail with rate limit
        processor.openai_client.embeddings.create.side_effect = Exception("HTTP Error 429: Too Many Requests")
        
        with pytest.raises(Exception):
            processor._create_embeddings(sample_chunks)
        
        # Should have retried the maximum number of times
        assert processor.openai_client.embeddings.create.call_count == 2
    
    def test_create_embeddings_batch_delay(self, processor, sample_chunks):
        """Test that batch requests include a small delay."""
        processor.batch_delay = 0.01  # Short delay for testing
        
        start_time = time.time()
        processor._create_embeddings(sample_chunks)
        end_time = time.time()
        
        # Should have included the batch delay
        assert end_time - start_time >= processor.batch_delay


class TestEmbeddingConfiguration:
    """Test embedding configuration and parameters."""
    
    def test_rate_limiting_configuration(self, processor):
        """Test that rate limiting parameters are properly configured."""
        # Should have default values
        assert processor.max_retries >= 1
        assert processor.base_delay > 0
        assert processor.batch_delay >= 0
    
    def test_embedding_model_configuration(self, processor):
        """Test that embedding model is configurable."""
        # Mock environment variable
        with patch.dict('os.environ', {'OPENAI_MODEL_NAME': 'text-embedding-3-small'}):
            processor._create_embeddings([])
        
        # Should not call API for empty chunks, but model should be configurable 