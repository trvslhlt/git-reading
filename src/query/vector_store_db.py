"""
Vector store implementation using SQLite for metadata and FAISS for vectors.

This version stores note metadata in SQLite (via load module) while keeping
FAISS for vector search. Provides better query capabilities and easier
enrichment integration.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from common.logger import get_logger
from load.db_schema import get_connection

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Represents a search result with note data and metadata."""

    note_id: int
    excerpt: str
    book_title: str
    author_first_name: str
    author_last_name: str
    section: str
    similarity: float
    page_number: int | None = None
    book_id: str | None = None
    author_id: str | None = None

    @property
    def author(self) -> str:
        """Get full author name for backward compatibility."""
        if self.author_first_name and self.author_last_name:
            return f"{self.author_first_name} {self.author_last_name}"
        return self.author_last_name or self.author_first_name or "Unknown"


class VectorStoreDB:
    """
    FAISS-based vector store with SQLite metadata storage.

    Vectors are stored in FAISS for fast similarity search.
    Note metadata is stored in SQLite for rich queries and easy enrichment.
    """

    def __init__(self, dimension: int, db_path: str | Path):
        """
        Initialize the vector store with database.

        Args:
            dimension: Dimension of the embedding vectors
            db_path: Path to SQLite database file
        """
        self.dimension = dimension
        self.db_path = Path(db_path)
        self.index = faiss.IndexFlatL2(dimension)

    def add(self, embeddings: np.ndarray, note_ids: list[int]):
        """
        Add embeddings for notes that already exist in the database.

        Args:
            embeddings: numpy array of shape (n, dimension)
            note_ids: list of note IDs from the database
        """
        if len(embeddings) != len(note_ids):
            raise ValueError("Number of embeddings must match number of note IDs")

        # Normalize embeddings for cosine similarity
        normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Add to FAISS index
        self.index.add(normalized.astype(np.float32))

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_author: str | None = None,
        filter_section: str | None = None,
        filter_book: str | None = None,
    ) -> list[SearchResult]:
        """
        Search for similar text notes with SQL-based filtering.

        Args:
            query_embedding: numpy array of shape (dimension,)
            k: number of results to return
            filter_author: Optional author name to filter by
            filter_section: Optional section name to filter by
            filter_book: Optional book title to filter by

        Returns:
            List of SearchResult objects, ordered by relevance
        """
        if self.index.ntotal == 0:
            return []

        # Normalize query for cosine similarity
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        query_norm = query_norm.reshape(1, -1).astype(np.float32)

        # Build SQL query for filtering
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        # Get valid note IDs based on filters
        sql_parts = [
            """
            SELECT n.id, n.faiss_index
            FROM notes n
            JOIN books b ON n.book_id = b.id
            JOIN book_authors ba ON b.id = ba.book_id
            JOIN authors a ON ba.author_id = a.id
            WHERE 1=1
        """
        ]
        params = []

        if filter_author:
            sql_parts.append("AND a.name = ?")
            params.append(filter_author)

        if filter_section:
            sql_parts.append("AND n.section = ?")
            params.append(filter_section)

        if filter_book:
            sql_parts.append("AND b.title = ?")
            params.append(filter_book)

        sql_parts.append("ORDER BY n.faiss_index")

        query_sql = "\n".join(sql_parts)
        cursor.execute(query_sql, params)
        filtered_notes = cursor.fetchall()

        if not filtered_notes:
            conn.close()
            return []

        # Extract faiss indices for filtered notes
        note_id_to_faiss = {row[0]: row[1] for row in filtered_notes}
        faiss_indices = [row[1] for row in filtered_notes]

        # PRE-FILTERING: Search only filtered vectors if filters applied
        if filter_author or filter_section or filter_book:
            # Extract only the filtered embeddings
            filtered_vectors = np.array([self.index.reconstruct(int(idx)) for idx in faiss_indices])

            # Create temporary index with just filtered vectors
            temp_index = faiss.IndexFlatL2(self.dimension)
            temp_index.add(filtered_vectors.astype(np.float32))

            # Search the filtered index
            distances, temp_indices = temp_index.search(query_norm, min(k, len(faiss_indices)))

            # Map temporary indices back to original faiss indices
            original_faiss_indices = [faiss_indices[i] for i in temp_indices[0]]

        else:
            # No filters - search everything
            distances, indices = self.index.search(query_norm, min(k, self.index.ntotal))
            original_faiss_indices = indices[0].tolist()

        # Convert distances to similarity scores
        similarities = 1 - (distances[0] ** 2 / 2)

        # Get note details from database
        faiss_to_note_id = {v: k for k, v in note_id_to_faiss.items()}

        results = []
        for faiss_idx, similarity in zip(original_faiss_indices, similarities, strict=True):
            note_id = faiss_to_note_id.get(faiss_idx)
            if note_id is None:
                continue

            # Fetch full note details
            cursor.execute(
                """
                SELECT n.id, n.excerpt, n.section, n.page_number, n.book_id,
                       b.title, a.id as author_id, a.first_name, a.last_name
                FROM notes n
                JOIN books b ON n.book_id = b.id
                JOIN book_authors ba ON b.id = ba.book_id
                JOIN authors a ON ba.author_id = a.id
                WHERE n.id = ?
            """,
                (note_id,),
            )
            row = cursor.fetchone()

            if row:
                results.append(
                    SearchResult(
                        note_id=row[0],
                        excerpt=row[1],
                        section=row[2],
                        page_number=row[3],
                        book_id=row[4],
                        book_title=row[5],
                        author_id=row[6],
                        author_first_name=row[7],
                        author_last_name=row[8],
                        similarity=float(similarity),
                    )
                )

        conn.close()
        return results

    def save(self, directory: Path):
        """
        Save the FAISS index to disk (database is already persisted).

        Args:
            directory: Directory to save the index in
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = directory / "faiss.index"
        faiss.write_index(self.index, str(index_path))

        # Save metadata about the store
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM notes")
        num_notes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM books")
        num_books = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM authors")
        num_authors = cursor.fetchone()[0]

        conn.close()

        metadata = {
            "dimension": self.dimension,
            "num_vectors": self.index.ntotal,
            "num_notes": num_notes,
            "num_authors": num_authors,
            "num_books": num_books,
            "database_path": str(self.db_path),
        }
        metadata_path = directory / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Saved vector store to {directory}")
        logger.info(f"  - [bold]{self.index.ntotal}[/bold] vectors")
        logger.info(f"  - [bold]{num_notes}[/bold] notes in database")
        logger.info(f"  - [bold]{num_authors}[/bold] authors")
        logger.info(f"  - [bold]{num_books}[/bold] books")

    @classmethod
    def load(cls, directory: Path) -> "VectorStoreDB":
        """
        Load a vector store from disk.

        Args:
            directory: Directory containing the saved store

        Returns:
            Loaded VectorStoreDB instance
        """
        directory = Path(directory)

        # Load metadata
        metadata_path = directory / "metadata.json"
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Create instance
        db_path = metadata["database_path"]
        store = cls(dimension=metadata["dimension"], db_path=db_path)

        # Load FAISS index
        index_path = directory / "faiss.index"
        store.index = faiss.read_index(str(index_path))

        logger.info(f"Loaded vector store from {directory}")
        logger.info(f"  - [bold]{store.index.ntotal}[/bold] vectors")
        logger.info(f"  - Database: {db_path}")

        return store

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the vector store and database."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM notes")
        num_notes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM books")
        num_books = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM authors")
        num_authors = cursor.fetchone()[0]

        cursor.execute("SELECT name FROM authors ORDER BY name")
        authors = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT section FROM notes WHERE section != '' ORDER BY section")
        sections = [row[0] for row in cursor.fetchall()]

        conn.close()

        return {
            "total_notes": num_notes,
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "unique_authors": num_authors,
            "unique_books": num_books,
            "unique_sections": len(sections),
            "authors": authors,
            "sections": sections,
        }
