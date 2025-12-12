"""Migrate from index.json to SQLite database.

This script migrates the existing index.json structure to a relational SQLite database
while preserving the FAISS vector store.
"""

import json
import sqlite3
from pathlib import Path

from common.logger import get_logger
from extract.replay import get_latest_extraction, get_new_extractions_since, replay_all_extractions
from load.db_schema import create_database, get_connection

from .db_utils import generate_author, generate_author_id, generate_book_id

logger = get_logger(__name__)


def get_checkpoint(conn: sqlite3.Connection) -> str | None:
    """Get last processed commit hash from database.

    Args:
        conn: Database connection

    Returns:
        Last processed commit hash or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM metadata WHERE key = 'last_processed_commit'")
    row = cursor.fetchone()
    return row[0] if row else None


def store_checkpoint(conn: sqlite3.Connection, commit_hash: str) -> None:
    """Store last processed commit hash in database.

    Args:
        conn: Database connection
        commit_hash: Git commit hash to store
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO metadata (key, value)
        VALUES ('last_processed_commit', ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=CURRENT_TIMESTAMP
        """,
        (commit_hash,),
    )
    conn.commit()


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
        logger.info(f"Loading data from {json_path}...")
    with open(json_path) as f:
        data = json.load(f)

    books = data.get("books", [])
    if verbose:
        logger.info(f"Found [bold]{len(books)}[/bold] books")

    # Flatten books into chunks
    chunks = []
    for book in books:
        title = book.get("title", "Unknown")
        first_name = book.get("author_first_name", "Unknown")
        last_name = book.get("author_last_name", "Unknown")
        sections_data = book.get("sections", {})

        for section_name, excerpts in sections_data.items():
            if isinstance(excerpts, list):
                for excerpt in excerpts:
                    chunks.append(
                        {
                            "title": title,
                            "author_first_name": first_name,
                            "author_last_name": last_name,
                            "section": section_name,
                            "excerpt": excerpt,
                        }
                    )

    if verbose:
        logger.info(f"Extracted [bold]{len(chunks)}[/bold] chunks from books")

    # Create database
    if verbose:
        logger.info(f"Creating database at {db_path}...")
    create_database(db_path)

    # Connect and migrate
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Track unique books and authors
    books_seen: dict[str, dict] = {}
    authors_seen: dict[str, str] = {}  # name -> id mapping

    if verbose:
        logger.info("Migrating data...")

    for i, chunk in enumerate(chunks):
        # Extract data from chunk
        title = chunk.get("title", "Unknown")

        # Extract author name parts
        author_first_name = chunk.get("author_first_name", "")
        author_last_name = chunk.get("author_last_name", "")
        author = generate_author(author_first_name, author_last_name)

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
            logger.debug(f"  Processed {i + 1}/{len(chunks)} chunks...")

    conn.commit()

    # Print summary
    if verbose:
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM authors")
        author_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]

        logger.info("\n[green]✓[/green] Migration complete!")
        logger.info(f"  Books: [bold]{book_count}[/bold]")
        logger.info(f"  Authors: [bold]{author_count}[/bold]")
        logger.info(f"  Chunks: [bold]{chunk_count}[/bold]")

    conn.close()


def migrate_from_extractions(index_dir: Path, db_path: Path, verbose: bool = True) -> None:
    """Migrate data from extraction files to SQLite database (full rebuild).

    Args:
        index_dir: Directory containing extraction files
        db_path: Path to SQLite database file
        verbose: Print progress messages

    Raises:
        ValueError: If no extraction files found
    """
    index_dir = Path(index_dir)
    db_path = Path(db_path)

    if not index_dir.exists():
        raise FileNotFoundError(f"Index directory not found: {index_dir}")

    # Replay all extractions to get current state
    if verbose:
        logger.info(f"Replaying all extractions from {index_dir}...")
    items = replay_all_extractions(index_dir)

    if not items:
        raise ValueError(f"No items found in extraction files at {index_dir}")

    if verbose:
        logger.info(f"Found [bold]{len(items)}[/bold] items")

    # Create database
    if verbose:
        logger.info(f"Creating database at {db_path}...")
    create_database(db_path)

    # Connect and migrate
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Track unique books and authors
    books_seen: dict[str, dict] = {}
    authors_seen: dict[str, str] = {}  # name -> id mapping

    if verbose:
        logger.info("Migrating data...")

    for i, item in enumerate(items):
        # Extract data from item
        title = item.book_title
        author_first_name = item.author_first_name
        author_last_name = item.author_last_name
        author = generate_author(author_first_name, author_last_name)
        section = item.section
        excerpt = item.content

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

        # Insert chunk with item_id
        cursor.execute(
            """
            INSERT INTO chunks (item_id, book_id, section, excerpt, faiss_index)
            VALUES (?, ?, ?, ?, ?)
        """,
            (item.item_id, book_id, section, excerpt, i),
        )

        if verbose and (i + 1) % 500 == 0:
            logger.debug(f"  Processed {i + 1}/{len(items)} items...")

    # Store checkpoint (get latest extraction's commit hash)
    latest_extraction = get_latest_extraction(index_dir)
    if latest_extraction:
        store_checkpoint(conn, latest_extraction.extraction_metadata.git_commit_hash)

    conn.commit()

    # Print summary
    if verbose:
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM authors")
        author_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]

        logger.info("\n[green]✓[/green] Migration complete!")
        logger.info(f"  Books: [bold]{book_count}[/bold]")
        logger.info(f"  Authors: [bold]{author_count}[/bold]")
        logger.info(f"  Chunks: [bold]{chunk_count}[/bold]")

    conn.close()


def migrate_incremental(index_dir: Path, db_path: Path, verbose: bool = True) -> None:
    """Apply incremental updates from extraction files to existing database.

    Args:
        index_dir: Directory containing extraction files
        db_path: Path to SQLite database file
        verbose: Print progress messages

    Raises:
        ValueError: If no checkpoint found or database doesn't exist
    """
    index_dir = Path(index_dir)
    db_path = Path(db_path)

    if not db_path.exists():
        raise ValueError(f"Database not found: {db_path}. Run full migration first.")

    # Connect to database
    conn = get_connection(db_path)

    # Get last processed commit
    last_commit = get_checkpoint(conn)
    if not last_commit:
        conn.close()
        raise ValueError("No checkpoint found in database. Run full migration first.")

    if verbose:
        logger.info(f"Last processed commit: {last_commit[:7]}")

    # Get new extractions since checkpoint
    new_extractions = get_new_extractions_since(index_dir, last_commit)

    if not new_extractions:
        if verbose:
            logger.info("[green]✓[/green] No new extractions to process")
        conn.close()
        return

    if verbose:
        logger.info(f"Found [bold]{len(new_extractions)}[/bold] new extraction(s)")

    cursor = conn.cursor()

    # Track stats
    adds = 0
    updates = 0
    deletes = 0

    # Process each extraction
    for extraction in new_extractions:
        if verbose:
            logger.debug(
                f"Processing extraction: {extraction.extraction_metadata.git_commit_hash[:7]}"
            )

        for item in extraction.items:
            author = generate_author(item.author_first_name, item.author_last_name)
            author_id = generate_author_id(author)
            book_id = generate_book_id(item.book_title, author)

            if item.operation == "add":
                # Ensure author exists
                cursor.execute(
                    """
                    INSERT INTO authors (id, first_name, last_name, name)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(name) DO NOTHING
                """,
                    (author_id, item.author_first_name, item.author_last_name, author),
                )

                # Ensure book exists
                cursor.execute(
                    """
                    INSERT INTO books (id, title)
                    VALUES (?, ?)
                    ON CONFLICT(id) DO NOTHING
                """,
                    (book_id, item.book_title),
                )

                # Link book to author
                cursor.execute(
                    """
                    INSERT INTO book_authors (book_id, author_id)
                    VALUES (?, ?)
                    ON CONFLICT DO NOTHING
                """,
                    (book_id, author_id),
                )

                # Get next faiss_index
                cursor.execute("SELECT MAX(faiss_index) FROM chunks")
                max_index = cursor.fetchone()[0]
                next_index = (max_index + 1) if max_index is not None else 0

                # Insert new chunk
                cursor.execute(
                    """
                    INSERT INTO chunks (item_id, book_id, section, excerpt, faiss_index)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (item.item_id, book_id, item.section, item.content, next_index),
                )
                adds += 1

            elif item.operation == "update":
                # Update existing chunk
                cursor.execute(
                    """
                    UPDATE chunks
                    SET section = ?, excerpt = ?
                    WHERE item_id = ?
                """,
                    (item.section, item.content, item.item_id),
                )
                updates += 1

            elif item.operation == "delete":
                # Delete chunk
                cursor.execute("DELETE FROM chunks WHERE item_id = ?", (item.item_id,))
                deletes += 1

        # Update checkpoint after each extraction
        store_checkpoint(conn, extraction.extraction_metadata.git_commit_hash)

    conn.commit()

    if verbose:
        logger.info("\n[green]✓[/green] Incremental migration complete!")
        logger.info(f"  Adds: [bold]{adds}[/bold]")
        logger.info(f"  Updates: [bold]{updates}[/bold]")
        logger.info(f"  Deletes: [bold]{deletes}[/bold]")

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
        logger.error(
            f"[red]✗[/red] Chunk count mismatch: JSON={json_chunk_count}, DB={db_chunk_count}"
        )
        return False

    # Check that faiss_index values are sequential
    if faiss_indices != list(range(len(faiss_indices))):
        logger.error("[red]✗[/red] FAISS indices are not sequential")
        return False

    logger.info("[green]✓[/green] Migration verification passed")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        logger.error("Usage: python migrate_to_db.py <index.json> <database.db>")
        sys.exit(1)

    json_path = sys.argv[1]
    db_path = sys.argv[2]

    migrate_from_json(json_path, db_path, verbose=True)
    verify_migration(db_path, json_path)
