"""Migrate from index.json to SQLite database.

This script migrates the existing index.json structure to a relational SQLite database
while preserving the FAISS vector store.
"""

import json
import sqlite3
from pathlib import Path

from load.db_schema import create_database, get_connection


def generate_book_id(title: str, author: str) -> str:
    """Generate a stable book ID from title and author.

    Args:
        title: Book title
        author: Book author

    Returns:
        Stable book ID
    """
    # Simple slug: lowercase, replace spaces with hyphens, remove special chars
    slug = f"{author}_{title}".lower()
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    slug = "-".join(slug.split())
    return slug[:100]  # Limit length


def generate_author_id(name: str) -> str:
    """Generate a stable author ID from name.

    Args:
        name: Author name

    Returns:
        Stable author ID
    """
    slug = name.lower()
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    slug = "-".join(slug.split())
    return slug[:100]


def migrate_from_json(json_path: str | Path, db_path: str | Path, verbose: bool = True) -> None:
    """Migrate data from index.json to SQLite database.

    Args:
        json_path: Path to index.json file
        db_path: Path to SQLite database file
        verbose: Print progress messages
    """
    json_path = Path(json_path)
    db_path = Path(db_path)

    if not json_path.exists():
        raise FileNotFoundError(f"Index file not found: {json_path}")

    # Load JSON data
    if verbose:
        print(f"Loading data from {json_path}...")
    with open(json_path) as f:
        data = json.load(f)

    books = data.get("books", [])
    if verbose:
        print(f"Found {len(books)} books")

    # Flatten books into chunks
    chunks = []
    for book in books:
        title = book.get("title", "Unknown")
        author = book.get("author", "Unknown")
        sections_data = book.get("sections", {})

        for section_name, excerpts in sections_data.items():
            if isinstance(excerpts, list):
                for excerpt in excerpts:
                    chunks.append(
                        {
                            "title": title,
                            "author": author,
                            "section": section_name,
                            "excerpt": excerpt,
                        }
                    )

    if verbose:
        print(f"Extracted {len(chunks)} chunks from books")

    # Create database
    if verbose:
        print(f"Creating database at {db_path}...")
    create_database(db_path)

    # Connect and migrate
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Track unique books and authors
    books_seen: dict[str, dict] = {}
    authors_seen: dict[str, str] = {}  # name -> id mapping

    if verbose:
        print("Migrating data...")

    for i, chunk in enumerate(chunks):
        # Extract data from chunk
        title = chunk.get("title", "Unknown")

        # Extract author name parts
        author_first_name = chunk.get("author_first_name", "")
        author_last_name = chunk.get("author_last_name", "")

        # Generate full name for compatibility
        if author_first_name and author_last_name:
            author = f"{author_first_name} {author_last_name}"
        elif author_last_name:
            author = author_last_name
        elif author_first_name:
            author = author_first_name
        else:
            author = "Unknown"

        section = chunk.get("section", "")
        excerpt = chunk.get("excerpt", "")

        # Generate IDs
        author_id = generate_author_id(author)
        book_id = generate_book_id(title, author)

        # Insert author if not seen
        if author not in authors_seen:
            try:
                cursor.execute(
                    """
                    INSERT INTO authors (id, first_name, last_name, name)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET
                        first_name=excluded.first_name,
                        last_name=excluded.last_name
                """,
                    (author_id, author_first_name, author_last_name, author),
                )
                authors_seen[author] = author_id
            except sqlite3.IntegrityError:
                # Author already exists
                authors_seen[author] = author_id

        # Insert book if not seen
        if book_id not in books_seen:
            try:
                cursor.execute(
                    """
                    INSERT INTO books (id, title)
                    VALUES (?, ?)
                    ON CONFLICT(id) DO UPDATE SET title=title
                """,
                    (book_id, title),
                )
                books_seen[book_id] = {"title": title, "author": author}

                # Link book to author
                cursor.execute(
                    """
                    INSERT INTO book_authors (book_id, author_id)
                    VALUES (?, ?)
                    ON CONFLICT DO NOTHING
                """,
                    (book_id, author_id),
                )
            except sqlite3.IntegrityError:
                # Book already exists
                pass

        # Insert chunk
        cursor.execute(
            """
            INSERT INTO chunks (book_id, section, excerpt, faiss_index)
            VALUES (?, ?, ?, ?)
        """,
            (book_id, section, excerpt, i),
        )

        if verbose and (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(chunks)} chunks...")

    conn.commit()

    # Print summary
    if verbose:
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM authors")
        author_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]

        print("\nMigration complete!")
        print(f"  Books: {book_count}")
        print(f"  Authors: {author_count}")
        print(f"  Chunks: {chunk_count}")

    conn.close()


def verify_migration(db_path: str | Path, json_path: str | Path) -> bool:
    """Verify that migration preserved all data.

    Args:
        db_path: Path to SQLite database
        json_path: Path to original JSON file

    Returns:
        True if verification passes
    """
    # Load JSON and count chunks
    with open(json_path) as f:
        data = json.load(f)

    books = data.get("books", [])
    json_chunk_count = 0
    for book in books:
        sections_data = book.get("sections", {})
        for _, excerpts in sections_data.items():
            if isinstance(excerpts, list):
                json_chunk_count += len(excerpts)

    # Check DB
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM chunks")
    db_chunk_count = cursor.fetchone()[0]

    cursor.execute("SELECT faiss_index FROM chunks ORDER BY faiss_index")
    faiss_indices = [row[0] for row in cursor.fetchall()]

    conn.close()

    # Verify
    if json_chunk_count != db_chunk_count:
        print(f"❌ Chunk count mismatch: JSON={json_chunk_count}, DB={db_chunk_count}")
        return False

    # Check that faiss_index values are sequential
    if faiss_indices != list(range(len(faiss_indices))):
        print("❌ FAISS indices are not sequential")
        return False

    print("✅ Migration verification passed")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python migrate_to_db.py <index.json> <database.db>")
        sys.exit(1)

    json_path = sys.argv[1]
    db_path = sys.argv[2]

    migrate_from_json(json_path, db_path, verbose=True)
    verify_migration(db_path, json_path)
