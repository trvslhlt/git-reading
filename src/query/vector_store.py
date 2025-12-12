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

from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextNote:
    """Represents a note of text with metadata."""

    text: str
    book_title: str
    author_first_name: str
    author_last_name: str
    section: str
    source_file: str
    date_read: str | None = None
    note_id: str | None = None
    item_id: str | None = None  # For tracking across incremental updates

    @property
    def author(self) -> str:
        """Get full author name for backward compatibility."""
        if self.author_first_name and self.author_last_name:
            return f"{self.author_first_name} {self.author_last_name}"
        return self.author_last_name or self.author_first_name or "Unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["author"] = self.author  # Add computed full name
        return d


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
        self.notes: list[TextNote] = []

        # Build lookup tables for fast filtering
        self.author_to_indices: dict[str, list[int]] = {}
        self.section_to_indices: dict[str, list[int]] = {}
        self.book_to_indices: dict[str, list[int]] = {}

        # Track item_id to faiss_index mapping for incremental updates
        self.item_id_to_index: dict[str, int] = {}
        self.deleted_indices: set[int] = set()  # Track deleted items
        self.checkpoint: str | None = None  # Last processed commit hash

    def add(self, embeddings: np.ndarray, notes: list[TextNote]):
        """
        Add embeddings and their associated notes to the store.

        Args:
            embeddings: numpy array of shape (n, dimension)
            notes: list of TextNote objects corresponding to each embedding
        """
        if len(embeddings) != len(notes):
            raise ValueError("Number of embeddings must match number of notes")

        # Get the starting index for new notes
        start_idx = len(self.notes)

        # Normalize embeddings for cosine similarity
        normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Add to FAISS index
        self.index.add(normalized.astype(np.float32))

        # Store note metadata and build lookup tables
        for i, note in enumerate(notes):
            idx = start_idx + i
            self.notes.append(note)

            # Track item_id mapping if available
            if note.item_id:
                self.item_id_to_index[note.item_id] = idx

            # Build author lookup
            if note.author not in self.author_to_indices:
                self.author_to_indices[note.author] = []
            self.author_to_indices[note.author].append(idx)

            # Build section lookup
            if note.section not in self.section_to_indices:
                self.section_to_indices[note.section] = []
            self.section_to_indices[note.section].append(idx)

            # Build book lookup
            if note.book_title not in self.book_to_indices:
                self.book_to_indices[note.book_title] = []
            self.book_to_indices[note.book_title].append(idx)

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_author: str | None = None,
        filter_section: str | None = None,
        filter_book: str | None = None,
    ) -> list[tuple[TextNote, float]]:
        """
        Search for similar text notes with optional pre-filtering.

        Pre-filtering approach: Extract filtered embeddings, search only those,
        then map back to original notes. Much faster than post-filtering for
        selective filters.

        Args:
            query_embedding: numpy array of shape (dimension,)
            k: number of results to return
            filter_author: Optional author name to filter by (pre-filter)
            filter_section: Optional section name to filter by (pre-filter)
            filter_book: Optional book title to filter by (pre-filter)

        Returns:
            List of (TextNote, similarity_score) tuples, ordered by relevance
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

        # Gather results, skipping deleted indices
        results = []
        for idx, similarity in zip(original_indices, similarities, strict=True):
            if 0 <= idx < len(self.notes) and idx not in self.deleted_indices:
                results.append((self.notes[idx], float(similarity)))

        return results

    def remove_by_item_id(self, item_id: str) -> bool:
        """
        Mark an item as deleted by item_id.

        FAISS doesn't support true deletion, so we track deleted indices
        and filter them out during search.

        Args:
            item_id: The item ID to mark as deleted

        Returns:
            True if item was found and marked as deleted
        """
        if item_id in self.item_id_to_index:
            idx = self.item_id_to_index[item_id]
            self.deleted_indices.add(idx)
            # Note: We don't remove from item_id_to_index in case item is re-added
            return True
        return False

    def set_checkpoint(self, commit_hash: str):
        """
        Set the checkpoint (last processed commit hash).

        Args:
            commit_hash: Git commit hash
        """
        self.checkpoint = commit_hash

    def get_checkpoint(self) -> str | None:
        """
        Get the checkpoint (last processed commit hash).

        Returns:
            Last processed commit hash or None
        """
        return self.checkpoint

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

        # Save notes metadata
        notes_path = directory / "notes.pkl"
        with open(notes_path, "wb") as f:
            pickle.dump(self.notes, f)

        # Save lookup tables for fast loading
        lookups_path = directory / "lookups.pkl"
        lookups = {
            "author_to_indices": self.author_to_indices,
            "section_to_indices": self.section_to_indices,
            "book_to_indices": self.book_to_indices,
            "item_id_to_index": self.item_id_to_index,
            "deleted_indices": self.deleted_indices,
            "checkpoint": self.checkpoint,
        }
        with open(lookups_path, "wb") as f:
            pickle.dump(lookups, f)

        # Save metadata about the store
        metadata = {
            "dimension": self.dimension,
            "num_vectors": self.index.ntotal,
            "num_notes": len(self.notes),
            "num_authors": len(self.author_to_indices),
            "num_sections": len(self.section_to_indices),
            "num_books": len(self.book_to_indices),
        }
        metadata_path = directory / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved filtered vector store to {directory}")
        logger.info(f"  - [bold]{self.index.ntotal}[/bold] vectors")
        logger.info(f"  - [bold]{len(self.notes)}[/bold] notes")
        logger.info(f"  - [bold]{len(self.author_to_indices)}[/bold] authors")
        logger.info(f"  - [bold]{len(self.section_to_indices)}[/bold] sections")

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

        # Load notes
        notes_path = directory / "notes.pkl"
        with open(notes_path, "rb") as f:
            store.notes = pickle.load(f)

        # Load lookup tables
        lookups_path = directory / "lookups.pkl"
        with open(lookups_path, "rb") as f:
            lookups = pickle.load(f)
            store.author_to_indices = lookups["author_to_indices"]
            store.section_to_indices = lookups["section_to_indices"]
            store.book_to_indices = lookups["book_to_indices"]
            store.item_id_to_index = lookups.get("item_id_to_index", {})
            store.deleted_indices = lookups.get("deleted_indices", set())
            store.checkpoint = lookups.get("checkpoint")

        logger.info(f"Loaded filtered vector store from {directory}")
        logger.info(f"  - [bold]{store.index.ntotal}[/bold] vectors")
        logger.info(f"  - [bold]{len(store.notes)}[/bold] notes")
        logger.info(f"  - [bold]{len(store.author_to_indices)}[/bold] authors indexed")

        return store

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            "total_notes": len(self.notes),
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
        Get information about how many notes match the given filters.

        Useful for understanding filter selectivity before searching.
        """
        total = len(self.notes)

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
            "total_notes": total,
            "author_notes": author_count if author else None,
            "section_notes": section_count if section else None,
            "filtered_notes": filtered_count,
            "reduction_percent": ((total - filtered_count) / total * 100) if total > 0 else 0,
        }
