"""Database schema definition for git-reading metadata storage.

This module defines the SQLite schema for storing book metadata, author information,
and chunk references that complement the FAISS vector store.
"""

import sqlite3
from pathlib import Path


def create_database(db_path: str | Path) -> None:
    """Create SQLite database with schema for reading notes metadata.

    Args:
        db_path: Path to SQLite database file
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Books table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            isbn TEXT,
            publication_year INTEGER,
            publisher TEXT,
            page_count INTEGER,
            language TEXT,
            description TEXT,
            cover_url TEXT,
            goodreads_rating REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Authors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            birth_year INTEGER,
            death_year INTEGER,
            nationality TEXT,
            bio TEXT,
            wikipedia_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Book-Author relationship (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_authors (
            book_id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            author_role TEXT DEFAULT 'author',
            PRIMARY KEY (book_id, author_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    """)

    # Genres/subjects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            parent_id TEXT,
            FOREIGN KEY (parent_id) REFERENCES genres(id)
        )
    """)

    # Book-Genre relationship (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_genres (
            book_id TEXT NOT NULL,
            genre_id TEXT NOT NULL,
            PRIMARY KEY (book_id, genre_id),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
        )
    """)

    # Chunks table - references to excerpts with their vector positions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            section TEXT,
            excerpt TEXT NOT NULL,
            page_number INTEGER,
            faiss_index INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
    """)

    # Author influences (for graph exploration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS author_influences (
            influencer_id TEXT NOT NULL,
            influenced_id TEXT NOT NULL,
            relationship_type TEXT DEFAULT 'influenced',
            PRIMARY KEY (influencer_id, influenced_id),
            FOREIGN KEY (influencer_id) REFERENCES authors(id) ON DELETE CASCADE,
            FOREIGN KEY (influenced_id) REFERENCES authors(id) ON DELETE CASCADE
        )
    """)

    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_book_id ON chunks(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_faiss_index ON chunks(faiss_index)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_authors_book_id ON book_authors(book_id)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_book_authors_author_id ON book_authors(author_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_genres_book_id ON book_genres(book_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_book_genres_genre_id ON book_genres(genre_id)")

    conn.commit()
    conn.close()


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Get a connection to the database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLite connection with row factory enabled
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn
