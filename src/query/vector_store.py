"""
Vector store implementation with pre-filtering support using FAISS.

This version allows filtering vectors BEFORE search for better performance.
Builds lookup tables during indexing for fast metadata-based filtering.
"""

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""

    text: str
    book_title: str
    author: str
    section: str
    source_file: str
    date_read: str | None = None
    chunk_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class VectorStore:
    """
    FAISS-based vector store with pre-filtering support.

    This implementation uses lookup tables to filter vectors before search,
    which is much faster than post-filtering for selective filters.
    """

    def __init__(self, dimension: int):
        """
        Initialize the vector store.

        Args:
            dimension: Dimension of the embedding vectors
        """
        self.dimension = dimension
        # Use IndexFlatL2 which supports ID mapping
        self.index = faiss.IndexFlatL2(dimension)
        self.chunks: list[TextChunk] = []

        # Build lookup tables for fast filtering
        self.author_to_indices: dict[str, list[int]] = {}
        self.section_to_indices: dict[str, list[int]] = {}
        self.book_to_indices: dict[str, list[int]] = {}

    def add(self, embeddings: np.ndarray, chunks: list[TextChunk]):
        """
        Add embeddings and their associated chunks to the store.

        Args:
            embeddings: numpy array of shape (n, dimension)
            chunks: list of TextChunk objects corresponding to each embedding
        """
        if len(embeddings) != len(chunks):
            raise ValueError("Number of embeddings must match number of chunks")

        # Get the starting index for new chunks
        start_idx = len(self.chunks)

        # Normalize embeddings for cosine similarity
        normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Add to FAISS index
        self.index.add(normalized.astype(np.float32))

        # Store chunk metadata and build lookup tables
        for i, chunk in enumerate(chunks):
            idx = start_idx + i
            self.chunks.append(chunk)

            # Build author lookup
            if chunk.author not in self.author_to_indices:
                self.author_to_indices[chunk.author] = []
            self.author_to_indices[chunk.author].append(idx)

            # Build section lookup
            if chunk.section not in self.section_to_indices:
                self.section_to_indices[chunk.section] = []
            self.section_to_indices[chunk.section].append(idx)

            # Build book lookup
            if chunk.book_title not in self.book_to_indices:
                self.book_to_indices[chunk.book_title] = []
            self.book_to_indices[chunk.book_title].append(idx)

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_author: str | None = None,
        filter_section: str | None = None,
        filter_book: str | None = None,
    ) -> list[tuple[TextChunk, float]]:
        """
        Search for similar text chunks with optional pre-filtering.

        Pre-filtering approach: Extract filtered embeddings, search only those,
        then map back to original chunks. Much faster than post-filtering for
        selective filters.

        Args:
            query_embedding: numpy array of shape (dimension,)
            k: number of results to return
            filter_author: Optional author name to filter by (pre-filter)
            filter_section: Optional section name to filter by (pre-filter)
            filter_book: Optional book title to filter by (pre-filter)

        Returns:
            List of (TextChunk, similarity_score) tuples, ordered by relevance
        """
        if self.index.ntotal == 0:
            return []

        # Normalize query for cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        query_norm = query_norm.reshape(1, -1).astype(np.float32)

        # Determine which indices match filters
        valid_indices = None

        if filter_author:
            author_indices = self.author_to_indices.get(filter_author, [])
            valid_indices = set(author_indices) if author_indices else set()

        if filter_section:
            section_indices = self.section_to_indices.get(filter_section, [])
            section_set = set(section_indices) if section_indices else set()
            valid_indices = section_set if valid_indices is None else valid_indices & section_set

        if filter_book:
            book_indices = self.book_to_indices.get(filter_book, [])
            book_set = set(book_indices) if book_indices else set()
            valid_indices = book_set if valid_indices is None else valid_indices & book_set

        # If we have filters but no matches, return empty
        if valid_indices is not None and len(valid_indices) == 0:
            return []

        # PRE-FILTERING: Search only filtered vectors
        if valid_indices is not None:
            # Extract only the filtered embeddings
            valid_indices_list = sorted(valid_indices)
            filtered_vectors = np.array(
                [self.index.reconstruct(int(idx)) for idx in valid_indices_list]
            )

            # Create temporary index with just filtered vectors
            temp_index = faiss.IndexFlatL2(self.dimension)
            temp_index.add(filtered_vectors.astype(np.float32))

            # Search the filtered index
            distances, temp_indices = temp_index.search(query_norm, min(k, len(valid_indices_list)))

            # Map temporary indices back to original indices
            original_indices = np.array([valid_indices_list[i] for i in temp_indices[0]])

        else:
            # No filters - search everything
            distances, original_indices = self.index.search(query_norm, min(k, self.index.ntotal))
            original_indices = original_indices[0]

        # Convert distances to similarity scores
        # Since we're using L2 distance on normalized vectors:
        # cosine_similarity = 1 - (L2_distance^2 / 2)
        similarities = 1 - (distances[0] ** 2 / 2)

        # Gather results
        results = []
        for idx, similarity in zip(original_indices, similarities, strict=True):
            if 0 <= idx < len(self.chunks):
                results.append((self.chunks[idx], float(similarity)))

        return results

    def save(self, directory: Path):
        """
        Save the vector store to disk.

        Args:
            directory: Directory to save the store in
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = directory / "faiss.index"
        faiss.write_index(self.index, str(index_path))

        # Save chunks metadata
        chunks_path = directory / "chunks.pkl"
        with open(chunks_path, "wb") as f:
            pickle.dump(self.chunks, f)

        # Save lookup tables for fast loading
        lookups_path = directory / "lookups.pkl"
        lookups = {
            "author_to_indices": self.author_to_indices,
            "section_to_indices": self.section_to_indices,
            "book_to_indices": self.book_to_indices,
        }
        with open(lookups_path, "wb") as f:
            pickle.dump(lookups, f)

        # Save metadata about the store
        metadata = {
            "dimension": self.dimension,
            "num_vectors": self.index.ntotal,
            "num_chunks": len(self.chunks),
            "num_authors": len(self.author_to_indices),
            "num_sections": len(self.section_to_indices),
            "num_books": len(self.book_to_indices),
        }
        metadata_path = directory / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"Saved filtered vector store to {directory}")
        print(f"  - {self.index.ntotal} vectors")
        print(f"  - {len(self.chunks)} chunks")
        print(f"  - {len(self.author_to_indices)} authors")
        print(f"  - {len(self.section_to_indices)} sections")

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        """
        Load a vector store from disk.

        Args:
            directory: Directory containing the saved store

        Returns:
            Loaded VectorStore instance
        """
        directory = Path(directory)

        # Load metadata
        metadata_path = directory / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Create instance
        store = cls(dimension=metadata["dimension"])

        # Load FAISS index
        index_path = directory / "faiss.index"
        store.index = faiss.read_index(str(index_path))

        # Load chunks
        chunks_path = directory / "chunks.pkl"
        with open(chunks_path, "rb") as f:
            store.chunks = pickle.load(f)

        # Load lookup tables
        lookups_path = directory / "lookups.pkl"
        with open(lookups_path, "rb") as f:
            lookups = pickle.load(f)
            store.author_to_indices = lookups["author_to_indices"]
            store.section_to_indices = lookups["section_to_indices"]
            store.book_to_indices = lookups["book_to_indices"]

        print(f"Loaded filtered vector store from {directory}")
        print(f"  - {store.index.ntotal} vectors")
        print(f"  - {len(store.chunks)} chunks")
        print(f"  - {len(store.author_to_indices)} authors indexed")

        return store

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            "total_chunks": len(self.chunks),
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "unique_authors": len(self.author_to_indices),
            "unique_books": len(self.book_to_indices),
            "unique_sections": len(self.section_to_indices),
            "authors": list(self.author_to_indices.keys()),
            "sections": list(self.section_to_indices.keys()),
        }

    def get_filter_info(self, author: str | None = None, section: str | None = None) -> dict:
        """
        Get information about how many chunks match the given filters.

        Useful for understanding filter selectivity before searching.
        """
        total = len(self.chunks)

        if author:
            author_count = len(self.author_to_indices.get(author, []))
        else:
            author_count = total

        if section:
            section_count = len(self.section_to_indices.get(section, []))
        else:
            section_count = total

        # Intersection if both filters
        if author and section:
            author_set = set(self.author_to_indices.get(author, []))
            section_set = set(self.section_to_indices.get(section, []))
            filtered_count = len(author_set & section_set)
        elif author:
            filtered_count = author_count
        elif section:
            filtered_count = section_count
        else:
            filtered_count = total

        return {
            "total_chunks": total,
            "author_chunks": author_count if author else None,
            "section_chunks": section_count if section else None,
            "filtered_chunks": filtered_count,
            "reduction_percent": ((total - filtered_count) / total * 100) if total > 0 else 0,
        }
