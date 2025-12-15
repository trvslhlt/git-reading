"""Load data from extraction files to database.

This module loads data from extraction files into a relational database
while supporting incremental updates. It uses the database abstraction layer
to support both SQLite and PostgreSQL.
"""

from pathlib import Path

from common.logger import get_logger
from extract.replay import get_latest_extraction, get_new_extractions_since, replay_all_extractions
from load.db import DatabaseAdapter, IntegrityError, get_adapter

from .db_utils import generate_author, generate_author_id, generate_book_id

logger = get_logger(__name__)


def _set_log_level(verbose: bool) -> None:
    """Set logger level based on verbose flag."""
    if verbose:
        logger.setLevel("INFO")
    else:
        logger.setLevel("WARNING")


def get_checkpoint(adapter: DatabaseAdapter) -> str | None:
    """Get last processed commit hash from database.

    Args:
        adapter: Database adapter

    Returns:
        Last processed commit hash or None if not found
    """
    result = adapter.fetchone(
        "SELECT value FROM metadata WHERE key = ?", ("last_processed_commit",)
    )
    return result["value"] if result else None


def store_checkpoint(adapter: DatabaseAdapter, commit_hash: str) -> None:
    """Store last processed commit hash in database.

    Args:
        adapter: Database adapter
        commit_hash: Git commit hash to store
    """
    adapter.execute(
        """
        INSERT INTO metadata (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value=excluded.value,
            updated_at=CURRENT_TIMESTAMP
        """,
        ("last_processed_commit", commit_hash),
    )
    adapter.commit()


def load_from_extractions(index_dir: Path, verbose: bool = True, force: bool = False) -> None:
    """Load data from extraction files to database (full rebuild).

    Database configuration is read from environment variables.

    Args:
        index_dir: Directory containing extraction files
        verbose: Set to True for INFO level logging, False for WARNING level
        force: Drop existing tables before creating

    Raises:
        ValueError: If no extraction files found
    """
    _set_log_level(verbose)
    index_dir = Path(index_dir)

    if not index_dir.exists():
        raise FileNotFoundError(f"Index directory not found: {index_dir}")

    # Replay all extractions to get current state
    logger.info(f"Replaying all extractions from {index_dir}...")
    items = replay_all_extractions(index_dir)

    if not items:
        raise ValueError(f"No items found in extraction files at {index_dir}")

    logger.info(f"Found [bold]{len(items)}[/bold] items")

    # Create database
    logger.info("Creating database...")

    # For force flag, drop existing schema first
    if force:
        with get_adapter() as adapter:
            adapter.drop_schema()

    # Create schema
    with get_adapter() as adapter:
        adapter.create_schema()

    # Connect and load
    with get_adapter() as adapter:
        # Track unique books and authors
        books_seen: dict[str, dict] = {}
        authors_seen: dict[str, str] = {}  # name -> id mapping

        logger.info("Loading data...")

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
                    adapter.execute(
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
                except IntegrityError:
                    # Author already exists
                    authors_seen[author] = author_id

            # Insert book if not seen
            if book_id not in books_seen:
                try:
                    adapter.execute(
                        """
                        INSERT INTO books (id, title)
                        VALUES (?, ?)
                        ON CONFLICT(id) DO UPDATE SET title=EXCLUDED.title
                    """,
                        (book_id, title),
                    )
                    books_seen[book_id] = {"title": title, "author": author}

                    # Link book to author
                    adapter.execute(
                        """
                        INSERT INTO book_authors (book_id, author_id)
                        VALUES (?, ?)
                        ON CONFLICT DO NOTHING
                    """,
                        (book_id, author_id),
                    )
                except IntegrityError:
                    # Book already exists
                    pass

            # Insert note with item_id
            adapter.execute(
                """
                INSERT INTO notes (item_id, book_id, section, excerpt, faiss_index)
                VALUES (?, ?, ?, ?, ?)
            """,
                (item.item_id, book_id, section, excerpt, i),
            )

            if (i + 1) % 500 == 0:
                logger.debug(f"  Processed {i + 1}/{len(items)} items...")

        # Store checkpoint (get latest extraction's commit hash)
        latest_extraction = get_latest_extraction(index_dir)
        if latest_extraction:
            store_checkpoint(adapter, latest_extraction.extraction_metadata.git_commit_hash)

        # Print summary
        result = adapter.fetchone("SELECT COUNT(*) FROM books")
        book_count = result[list(result.keys())[0]]

        result = adapter.fetchone("SELECT COUNT(*) FROM authors")
        author_count = result[list(result.keys())[0]]

        result = adapter.fetchone("SELECT COUNT(*) FROM notes")
        note_count = result[list(result.keys())[0]]

        logger.info("\n[green]✓[/green] Load complete!")
        logger.info(f"  Books: [bold]{book_count}[/bold]")
        logger.info(f"  Authors: [bold]{author_count}[/bold]")
        logger.info(f"  Notes: [bold]{note_count}[/bold]")


def load_incremental(index_dir: Path, verbose: bool = True) -> None:
    """Apply incremental updates from extraction files to existing database.

    Database configuration is read from environment variables.

    Args:
        index_dir: Directory containing extraction files
        verbose: Set to True for INFO level logging, False for WARNING level

    Raises:
        ValueError: If no checkpoint found or database doesn't exist
    """
    _set_log_level(verbose)
    index_dir = Path(index_dir)

    # Check if database exists
    check_adapter = get_adapter()
    if not check_adapter.exists():
        raise ValueError("Database not found or has no tables. Run full load first.")

    # Connect to database
    with get_adapter() as adapter:
        # Get last processed commit
        last_commit = get_checkpoint(adapter)
        if not last_commit:
            raise ValueError("No checkpoint found in database. Run full load first.")

        logger.info(f"Last processed commit: {last_commit[:7]}")

        # Get new extractions since checkpoint
        new_extractions = get_new_extractions_since(index_dir, last_commit)

        if not new_extractions:
            logger.info("[green]✓[/green] No new extractions to process")
            return

        logger.info(f"Found [bold]{len(new_extractions)}[/bold] new extraction(s)")

        # Track stats
        adds = 0
        updates = 0
        deletes = 0

        # Process each extraction
        for extraction in new_extractions:
            logger.debug(
                f"Processing extraction: {extraction.extraction_metadata.git_commit_hash[:7]}"
            )

            for item in extraction.items:
                author = generate_author(item.author_first_name, item.author_last_name)
                author_id = generate_author_id(author)
                book_id = generate_book_id(item.book_title, author)

                if item.operation == "add":
                    # Ensure author exists
                    adapter.execute(
                        """
                        INSERT INTO authors (id, first_name, last_name, name)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(name) DO NOTHING
                    """,
                        (author_id, item.author_first_name, item.author_last_name, author),
                    )

                    # Ensure book exists
                    adapter.execute(
                        """
                        INSERT INTO books (id, title)
                        VALUES (?, ?)
                        ON CONFLICT(id) DO NOTHING
                    """,
                        (book_id, item.book_title),
                    )

                    # Link book to author
                    adapter.execute(
                        """
                        INSERT INTO book_authors (book_id, author_id)
                        VALUES (?, ?)
                        ON CONFLICT DO NOTHING
                    """,
                        (book_id, author_id),
                    )

                    # Get next faiss_index
                    result = adapter.fetchone("SELECT MAX(faiss_index) FROM notes")
                    max_index = result[list(result.keys())[0]] if result else None
                    next_index = (max_index + 1) if max_index is not None else 0

                    # Insert new note
                    adapter.execute(
                        """
                        INSERT INTO notes (item_id, book_id, section, excerpt, faiss_index)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (item.item_id, book_id, item.section, item.content, next_index),
                    )
                    adds += 1

                elif item.operation == "update":
                    # Update existing note
                    adapter.execute(
                        """
                        UPDATE notes
                        SET section = ?, excerpt = ?
                        WHERE item_id = ?
                    """,
                        (item.section, item.content, item.item_id),
                    )
                    updates += 1

                elif item.operation == "delete":
                    # Delete note
                    adapter.execute("DELETE FROM notes WHERE item_id = ?", (item.item_id,))
                    deletes += 1

            # Update checkpoint after each extraction
            store_checkpoint(adapter, extraction.extraction_metadata.git_commit_hash)

        logger.info("\n[green]✓[/green] Incremental load complete!")
        logger.info(f"  Adds: [bold]{adds}[/bold]")
        logger.info(f"  Updates: [bold]{updates}[/bold]")
        logger.info(f"  Deletes: [bold]{deletes}[/bold]")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.error("Usage: python -m load.load_data <index_dir>")
        logger.error("  Database configuration is read from .env")
        sys.exit(1)

    index_dir = Path(sys.argv[1])
    load_from_extractions(index_dir, verbose=True)
