#!/usr/bin/env python3
"""
Flame Documentation Processing Pipeline
Converts markdown files to chunks, creates embeddings, and stores in Qdrant.
"""

import os
import json
import logging
import hashlib
import re
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import tiktoken
from tqdm import tqdm
from openai import AzureOpenAI
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('processing.log'),
              logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Suppress noisy third-party logs that interfere with tqdm
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@dataclass
class DocumentChunk:
    """Represents a chunk of document content with metadata."""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str


class FlameDocsProcessor:
    """Main processor for Flame documentation."""

    def __init__(self, version: str = "1.7.0"):
        self.version = version
        self.source_dir = Path("_build/markdown")
        self.state_file = Path("processing_state.json")
        self.error_file = Path("processing_errors.json")

        # Initialize tokenizer for chunk sizing
        self.tokenizer = tiktoken.get_encoding(
            "cl100k_base")  # BG Note: we may need to change

        # Chunking parameters
        # BG Note: have a way to easily config this
        self.target_chunk_size = 900  # tokens
        self.overlap_size = 175  # tokens
        self.min_chunk_size = 100  # tokens

        # Rate limiting parameters
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
        self.base_delay = float(os.getenv("OPENAI_BASE_DELAY", "1.0"))
        self.batch_delay = float(os.getenv("OPENAI_BATCH_DELAY", "0.1"))

        # Initialize clients
        self._init_openai_client()
        self._init_qdrant_client()

        # Processing state
        self.processed_files = set()
        self.errors = []
        self.chunks_created = 0

        self._load_state()

    def _init_openai_client(self):
        """Initialize Azure OpenAI client."""
        self.openai_client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("OPENAI_API_BASE"),
        )

    def _init_qdrant_client(self):
        """Initialize Qdrant client and ensure collection exists."""
        self.qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_HOST"),
            port=os.getenv("QDRANT_PORT"),
        )
        self.collection_name = os.getenv("COLLECTION_NAME", "flame_docs")
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create Qdrant collection if it doesn't exist."""
        try:
            self.qdrant_client.get_collection(self.collection_name)
            logger.info(f"Collection '{self.collection_name}' already exists")
        except Exception:
            logger.info(f"Creating collection '{self.collection_name}'")
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536,
                                            distance=Distance.COSINE),
                hnsw_config=models.HnswConfigDiff(
                    m=16, 
                    ef_construct=200,
                    full_scan_threshold=10000
                ))

    def _load_state(self):
        """Load processing state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.processed_files = set(state.get(
                        'processed_files', []))
                    self.chunks_created = state.get('chunks_created', 0)
                logger.info(
                    f"Loaded state: {len(self.processed_files)} files processed"
                )
            except Exception as e:
                logger.warning(f"Could not load state file: {e}")

    def _save_state(self):
        """Save current processing state."""
        state = {
            'processed_files': list(self.processed_files),
            'chunks_created': self.chunks_created,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _save_errors(self):
        """Save error report."""
        if self.errors:
            with open(self.error_file, 'w') as f:
                json.dump(self.errors, f, indent=2)

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def _extract_metadata_from_path(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from file path."""
        relative_path = str(file_path.relative_to(self.source_dir))
        relative_parts = Path(relative_path).parts

        # Determine section from relative path
        section = relative_parts[0] if len(relative_parts) > 0 else "unknown"

        # Determine content type from path patterns
        content_type = "reference"
        if "tutorial" in relative_path.lower():
            content_type = "tutorial"
        elif "example" in relative_path.lower():
            content_type = "example"
        elif any(api_term in relative_path.lower()
                 for api_term in ["api", "reference"]):
            content_type = "api"

        return {
            "version": self.version,
            "file_path": relative_path,
            "section": section,
            "content_type": content_type
        }

    def _extract_heading_hierarchy(self, content: str) -> List[str]:
        """Extract heading hierarchy from markdown content."""
        headings = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                # Extract heading text, removing leading #'s and whitespace
                heading_text = line.lstrip('#').strip()
                if heading_text:
                    headings.append(heading_text)
        return headings

    def _detect_code_blocks(self, content: str) -> bool:
        """Detect if chunk contains significant code blocks."""
        code_patterns = [
            r'```[\s\S]*?```',  # Fenced code blocks
            r'`[^`\n]+`',  # Inline code
            r'^\s{4,}.*$'  # Indented code (simplified)
        ]

        code_content = ""
        for pattern in code_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            code_content += " ".join(matches)

        # Consider it has significant code if >20% is code or >100 chars of code
        code_ratio = len(code_content) / len(content) if content else 0
        return code_ratio > 0.2 or len(code_content) > 100

    def _split_by_headers(self, content: str) -> List[str]:
        """Split content by markdown headers while preserving structure."""
        sections = []
        current_section = []

        for line in content.split('\n'):
            if line.startswith('#') and current_section:
                # Save previous section
                sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            sections.append('\n'.join(current_section))

        return sections

    def _split_large_section(self, section: str, max_tokens: int) -> List[str]:
        """Split large sections by sentences/paragraphs with overlap."""
        if self._count_tokens(section) <= max_tokens:
            return [section]

        # Split by paragraphs first
        paragraphs = section.split('\n\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            test_chunk = current_chunk + "\n\n" + para if current_chunk else para

            if self._count_tokens(test_chunk) <= max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # Add overlap from previous chunk
                    overlap_text = self._get_text_overlap(
                        current_chunk, self.overlap_size)
                    current_chunk = overlap_text + "\n\n" + para
                else:
                    # Single paragraph too large - split more aggressively
                    current_chunk = para
                
                # If current chunk is still too large, split it by sentences
                while self._count_tokens(current_chunk) > max_tokens:
                    # Find a reasonable split point
                    sentences = current_chunk.split('. ')
                    if len(sentences) <= 1:
                        # Can't split further, just use what we have
                        break
                    
                    # Take roughly half the sentences
                    split_point = len(sentences) // 2
                    first_part = '. '.join(sentences[:split_point]) + '.'
                    second_part = '. '.join(sentences[split_point:])
                    
                    chunks.append(first_part)
                    current_chunk = second_part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _get_text_overlap(self, text: str, overlap_tokens: int) -> str:
        """Get last N tokens worth of text for overlap."""
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= overlap_tokens:
            return text

        overlap_token_ids = tokens[-overlap_tokens:]
        return self.tokenizer.decode(overlap_token_ids)

    def _create_chunks(self, file_path: Path,
                       content: str) -> List[DocumentChunk]:
        """Create chunks from markdown content."""
        base_metadata = self._extract_metadata_from_path(file_path)
        heading_hierarchy = self._extract_heading_hierarchy(content)

        # Extract title from first heading or filename
        title = heading_hierarchy[
            0] if heading_hierarchy else file_path.stem.replace('_',
                                                                ' ').title()

        # Split by headers first
        sections = self._split_by_headers(content)

        chunks = []
        i = 0
        while i < len(sections):
            section = sections[i]
            
            # Skip very small sections unless they're the only content or last section
            if (len(sections) > 1 and 
                self._count_tokens(section) < self.min_chunk_size and 
                i < len(sections) - 1):
                # Try to merge with next section
                sections[i + 1] = section + "\n\n" + sections[i + 1]
                i += 1
                continue

            # Split large sections
            section_chunks = self._split_large_section(section,
                                                       self.target_chunk_size)

            for j, chunk_content in enumerate(section_chunks):
                if not chunk_content.strip():
                    continue

                # Create chunk metadata
                chunk_metadata = base_metadata.copy()
                chunk_metadata.update({
                    "title":
                    title,
                    "heading_path":
                    heading_hierarchy,
                    "has_code":
                    self._detect_code_blocks(chunk_content),
                    "chunk_index":
                    len(chunks),
                    "doc_url":
                    f"/{base_metadata['file_path'].replace('.md', '.html')}"
                })

                # Create unique chunk ID
                chunk_id = hashlib.md5(
                    f"{file_path}_{len(chunks)}_{chunk_content[:100]}".encode(
                    )).hexdigest()

                chunk = DocumentChunk(content=chunk_content.strip(),
                                      metadata=chunk_metadata,
                                      chunk_id=chunk_id)
                chunks.append(chunk)
                self.chunks_created += 1
            
            i += 1

        return chunks

    def _create_embeddings(self,
                           chunks: List[DocumentChunk]) -> List[List[float]]:
        """Create embeddings for chunks using Azure OpenAI with rate limiting."""
        if not chunks:
            return []

        texts = [chunk.content for chunk in chunks]
        
        for attempt in range(self.max_retries):
            try:
                # Add small delay between requests to avoid rate limits
                if attempt > 0:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying embedding creation after {delay:.2f}s delay (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                elif len(texts) > 1:
                    # Small delay even on first attempt for batch requests
                    time.sleep(self.batch_delay)

                response = self.openai_client.embeddings.create(
                    input=texts,
                    model=os.getenv("OPENAI_MODEL_NAME"),
                )

                embeddings = [embedding.embedding for embedding in response.data]
                logger.debug(f"Created {len(embeddings)} embeddings successfully")
                return embeddings

            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if "429" in error_str or "rate limit" in error_str:
                    if attempt < self.max_retries - 1:
                        # Calculate exponential backoff with jitter
                        delay = self.base_delay * (2 ** attempt) + random.uniform(0, 2)
                        logger.warning(f"Rate limit hit, waiting {delay:.2f}s before retry {attempt + 1}/{self.max_retries}")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded after {self.max_retries} attempts")
                        raise
                else:
                    # Non-rate-limit error, don't retry
                    logger.error(f"Error creating embeddings: {e}")
                    raise
        
        # This should never be reached, but just in case
        raise Exception(f"Failed to create embeddings after {self.max_retries} attempts")

    def _store_in_qdrant(self, chunks: List[DocumentChunk],
                         embeddings: List[List[float]]):
        """Store chunks and embeddings in Qdrant."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            # Include content in the payload along with metadata
            payload = chunk.metadata.copy()
            payload["content"] = chunk.content
            
            point = PointStruct(id=chunk.chunk_id,
                                vector=embedding,
                                payload=payload)
            points.append(point)

        try:
            self.qdrant_client.upsert(collection_name=self.collection_name,
                                      points=points)
            logger.debug(f"Stored {len(points)} points in Qdrant")
        except Exception as e:
            logger.error(f"Error storing in Qdrant: {e}")
            raise

    def _process_file(self, file_path: Path) -> bool:
        """Process a single markdown file."""
        try:
            # Check if already processed
            if str(file_path) in self.processed_files:
                logger.debug(f"Skipping already processed: {file_path}")
                return True

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"Empty file: {file_path}")
                return True

            # Create chunks
            chunks = self._create_chunks(file_path, content)

            if not chunks:
                logger.warning(f"No chunks created for: {file_path}")
                return True

            # Create embeddings
            embeddings = self._create_embeddings(chunks)

            # Store in Qdrant
            self._store_in_qdrant(chunks, embeddings)

            # Mark as processed
            self.processed_files.add(str(file_path))

            logger.info(f"Processed {file_path}: {len(chunks)} chunks")
            return True

        except Exception as e:
            error_info = {
                "file": str(file_path),
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.errors.append(error_info)
            logger.error(f"Error processing {file_path}: {e}")
            return False

    def process_all_files(self):
        """Process all markdown files in the source directory."""
        # Find all markdown files
        md_files = list(self.source_dir.rglob("*.md"))

        if not md_files:
            logger.error(f"No markdown files found in {self.source_dir}")
            return

        logger.info(f"Found {len(md_files)} markdown files")

        # Filter out already processed files for progress bar
        remaining_files = [
            f for f in md_files if str(f) not in self.processed_files
        ]

        logger.info(f"Processing {len(remaining_files)} remaining files")

        # Process files with progress bar
        successful = 0
        failed = 0

        with tqdm(remaining_files, desc="Processing files") as pbar:
            for file_path in pbar:
                pbar.set_description(f"Processing {file_path.name}")

                if self._process_file(file_path):
                    successful += 1
                else:
                    failed += 1

                # Save state periodically
                if (successful + failed) % 10 == 0:
                    self._save_state()

                pbar.set_postfix({
                    'success': successful,
                    'failed': failed,
                    'chunks': self.chunks_created
                })

        # Final state save
        self._save_state()
        self._save_errors()

        logger.info(f"Processing complete!")
        logger.info(f"Successfully processed: {successful} files")
        logger.info(f"Failed: {failed} files")
        logger.info(f"Total chunks created: {self.chunks_created}")

        if self.errors:
            logger.warning(f"Errors written to {self.error_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Process Flame documentation")
    # BG Note: 
    parser.add_argument("--version",
                        default="1.29.0",
                        help="Documentation version")
    parser.add_argument("--reset",
                        action="store_true",
                        help="Reset processing state")

    args = parser.parse_args()

    processor = FlameDocsProcessor(version=args.version)

    if args.reset:
        processor.state_file.unlink(missing_ok=True)
        processor.error_file.unlink(missing_ok=True)
        logger.info("Reset processing state")

    processor.process_all_files()


if __name__ == "__main__":
    main()
