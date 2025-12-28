"""Test incremental load handling of book title changes.

This test verifies that when a book title changes in the source data,
the incremental load process correctly:
1. Creates a new book record with the new title
2. Updates notes to point to the new book
3. Cleans up the orphaned old book record
"""

import json
import os
from pathlib import Path

import pytest

from load.db.sqlite_adapter import SQLiteAdapter
from load.db_utils import generate_book_id
from load.load_data import load_from_extractions, load_incremental


@pytest.fixture
def sample_extractions(tmp_path):
    """Create sample extraction files for testing.

    Creates two extractions:
    1. Initial extraction with typo: "Homegoing" by Marilynne Robinson
    2. Updated extraction fixing typo: "Housekeeping" by Marilynne Robinson
    """
    index_dir = tmp_path / "index"
    index_dir.mkdir()

    # Extraction 1: Initial with typo
    extraction1 = {
        "extraction_metadata": {
            "timestamp": "2024-01-01T00:00:00",
            "git_commit_hash": "abc123",
            "git_commit_timestamp": "2024-01-01T00:00:00",
            "extraction_type": "full",
            "notes_directory": str(tmp_path / "notes"),
        },
        "items": [
            {
                "item_id": "item1",
                "operation": "add",
                "book_title": "Homegoing",  # TYPO
                "author_first_name": "Marilynne",
                "author_last_name": "Robinson",
                "section": "Introduction",
                "content": "This is a great book about housekeeping.",
                "source_file": "homegoing.md",
                "line_number": 10,
            }
        ],
    }

    # Extraction 2: Fixed typo
    extraction2 = {
        "extraction_metadata": {
            "timestamp": "2024-01-02T00:00:00",
            "git_commit_hash": "def456",
            "git_commit_timestamp": "2024-01-02T00:00:00",
            "extraction_type": "incremental",
            "previous_commit_hash": "abc123",
            "notes_directory": str(tmp_path / "notes"),
        },
        "items": [
            {
                "item_id": "item1",
                "book_title": "Housekeeping",  # FIXED
                "author_first_name": "Marilynne",
                "author_last_name": "Robinson",
                "section": "Introduction",
                "content": "This is a great book about housekeeping.",
                "source_file": "housekeeping.md",  # renamed file
                "line_number": 10,
                "operation": "update",  # This is an update
            }
        ],
    }

    # Return paths and extraction data
    return {
        "index_dir": index_dir,
        "extraction1": extraction1,
        "extraction1_file": index_dir / "extraction_abc123.json",
        "extraction2": extraction2,
        "extraction2_file": index_dir / "extraction_def456.json",
    }


def test_book_title_change_cleanup(tmp_path, sample_extractions, monkeypatch):
    """Test that changing a book title cleans up the old book record.

    Scenario:
    1. Initial load has 'Homegoing' by Marilynne Robinson (typo)
    2. Incremental load fixes title to 'Housekeeping'
    3. Old 'Homegoing' book should be deleted
    4. New 'Housekeeping' book should exist
    """
    db_path = tmp_path / "test.db"
    index_dir = sample_extractions["index_dir"]

    # Configure environment to use test database
    monkeypatch.setenv("DATABASE_TYPE", "sqlite")
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Write only the first extraction initially
    sample_extractions["extraction1_file"].write_text(
        json.dumps(sample_extractions["extraction1"], indent=2)
    )

    adapter = SQLiteAdapter(db_path)

    # Initial full load
    adapter.connect()
    adapter.create_schema()
    adapter.close()

    load_from_extractions(index_dir, verbose=False)

    # Verify initial state - should have "Homegoing"
    with SQLiteAdapter(db_path) as adapter:
        books = adapter.fetchall("SELECT id, title FROM books")
        assert len(books) == 1
        assert books[0]["title"] == "Homegoing"
        old_book_id = books[0]["id"]

    # Write the second extraction (title fix)
    sample_extractions["extraction2_file"].write_text(
        json.dumps(sample_extractions["extraction2"], indent=2)
    )

    # Run incremental load (processes second extraction)
    load_incremental(index_dir, verbose=False)

    # Verify final state
    with SQLiteAdapter(db_path) as adapter:
        # Should have only "Housekeeping" now
        books = adapter.fetchall("SELECT id, title FROM books ORDER BY title")
        assert len(books) == 1, f"Expected 1 book, found {len(books)}: {books}"
        assert books[0]["title"] == "Housekeeping"

        # Old "Homegoing" book should be gone
        old_book = adapter.fetchall("SELECT * FROM books WHERE id = ?", (old_book_id,))
        assert len(old_book) == 0, "Old book should have been deleted"

        # Note should point to new book
        new_book_id = generate_book_id("Housekeeping", "Marilynne Robinson")
        notes = adapter.fetchall("SELECT * FROM notes WHERE book_id = ?", (new_book_id,))
        assert len(notes) == 1, "Note should point to new book"

        # No orphaned book_authors
        orphaned_ba = adapter.fetchall("""
            SELECT * FROM book_authors
            WHERE book_id NOT IN (SELECT id FROM books)
        """)
        assert len(orphaned_ba) == 0, "No orphaned book_authors should exist"


def test_orphaned_book_subjects_cleanup(tmp_path, monkeypatch):
    """Test that orphaned book_subjects are cleaned up when a book is removed.

    Scenario:
    1. Book has enrichment data (subjects)
    2. Book title changes (creating new book)
    3. Old book's subjects should be cleaned up
    """
    db_path = tmp_path / "test.db"
    index_dir = tmp_path / "index"
    index_dir.mkdir()

    # Configure environment to use test database
    monkeypatch.setenv("DATABASE_TYPE", "sqlite")
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Create initial extraction
    extraction1 = {
        "extraction_metadata": {
            "timestamp": "2024-01-01T00:00:00",
            "git_commit_hash": "abc123",
            "git_commit_timestamp": "2024-01-01T00:00:00",
            "extraction_type": "full",
            "notes_directory": str(tmp_path / "notes"),
        },
        "items": [
            {
                "item_id": "item1",
                "operation": "add",
                "book_title": "Homegoing",
                "author_first_name": "Marilynne",
                "author_last_name": "Robinson",
                "section": "Introduction",
                "content": "Test content.",
                "source_file": "homegoing.md",
                "line_number": 10,
            }
        ],
    }

    extraction1_file = index_dir / "extraction_abc123.json"
    extraction1_file.write_text(json.dumps(extraction1, indent=2))

    # Create database and do initial load
    adapter = SQLiteAdapter(db_path)
    adapter.connect()
    adapter.create_schema()
    adapter.close()

    load_from_extractions(index_dir, verbose=False)

    # Add enrichment data (subjects) to the book
    with SQLiteAdapter(db_path) as adapter:
        old_book_id = generate_book_id("Homegoing", "Marilynne Robinson")

        # Add a subject
        adapter.execute(
            "INSERT INTO subjects (id, name) VALUES (?, ?)",
            ("fiction", "Fiction"),
        )

        # Link subject to book
        adapter.execute(
            "INSERT INTO book_subjects (book_id, subject_id, source) VALUES (?, ?, ?)",
            (old_book_id, "fiction", "openlibrary"),
        )

        # Verify enrichment exists
        book_subjects = adapter.fetchall(
            "SELECT * FROM book_subjects WHERE book_id = ?", (old_book_id,)
        )
        assert len(book_subjects) == 1

    # Create extraction with title change
    extraction2 = {
        "extraction_metadata": {
            "timestamp": "2024-01-02T00:00:00",
            "git_commit_hash": "def456",
            "git_commit_timestamp": "2024-01-02T00:00:00",
            "extraction_type": "incremental",
            "previous_commit_hash": "abc123",
            "notes_directory": str(tmp_path / "notes"),
        },
        "items": [
            {
                "item_id": "item1",
                "book_title": "Housekeeping",  # Title changed
                "author_first_name": "Marilynne",
                "author_last_name": "Robinson",
                "section": "Introduction",
                "content": "Test content.",
                "source_file": "housekeeping.md",
                "line_number": 10,
                "operation": "update",
            }
        ],
    }

    extraction2_file = index_dir / "extraction_def456.json"
    extraction2_file.write_text(json.dumps(extraction2, indent=2))

    # Run incremental load
    load_incremental(index_dir, verbose=False)

    # Verify cleanup
    with SQLiteAdapter(db_path) as adapter:
        # Old book should be gone
        old_books = adapter.fetchall("SELECT * FROM books WHERE id = ?", (old_book_id,))
        assert len(old_books) == 0, "Old book should be deleted"

        # New book should exist
        new_book_id = generate_book_id("Housekeeping", "Marilynne Robinson")
        new_books = adapter.fetchall("SELECT * FROM books WHERE id = ?", (new_book_id,))
        assert len(new_books) == 1, "New book should exist"

        # Orphaned book_subjects should be cleaned up
        orphaned_subjects = adapter.fetchall(
            """
            SELECT * FROM book_subjects
            WHERE book_id NOT IN (SELECT id FROM books)
            """
        )
        assert len(orphaned_subjects) == 0, "Orphaned book_subjects should be cleaned up"

        # Orphaned subject should also be cleaned up (no books use it anymore)
        subjects = adapter.fetchall("SELECT * FROM subjects WHERE id = ?", ("fiction",))
        assert len(subjects) == 0, "Orphaned subject should be deleted"


def test_multiple_title_changes(tmp_path, monkeypatch):
    """Test multiple title changes across different extractions.

    Scenario:
    1. Book A: title changes
    2. Book B: title changes
    3. Book C: title stays same
    4. Only old versions of A and B should be cleaned up
    """
    db_path = tmp_path / "test.db"
    index_dir = tmp_path / "index"
    index_dir.mkdir()

    # Configure environment to use test database
    monkeypatch.setenv("DATABASE_TYPE", "sqlite")
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Create initial extraction with 3 books
    extraction1 = {
        "extraction_metadata": {
            "timestamp": "2024-01-01T00:00:00",
            "git_commit_hash": "abc123",
            "git_commit_timestamp": "2024-01-01T00:00:00",
            "extraction_type": "full",
            "notes_directory": str(tmp_path / "notes"),
        },
        "items": [
            {
                "item_id": "item1",
                "operation": "add",
                "book_title": "Homegoing",  # Will change to Housekeeping
                "author_first_name": "Marilynne",
                "author_last_name": "Robinson",
                "section": "Introduction",
                "content": "Book A content.",
                "source_file": "bookA.md",
                "line_number": 10,
            },
            {
                "item_id": "item2",
                "operation": "add",
                "book_title": "Mony",  # Will change to Money (typo fix)
                "author_first_name": "Martin",
                "author_last_name": "Amis",
                "section": "Chapter 1",
                "content": "Book B content.",
                "source_file": "bookB.md",
                "line_number": 20,
            },
            {
                "item_id": "item3",
                "operation": "add",
                "book_title": "Foundation",  # Stays the same
                "author_first_name": "Isaac",
                "author_last_name": "Asimov",
                "section": "Prologue",
                "content": "Book C content.",
                "source_file": "bookC.md",
                "line_number": 30,
            },
        ],
    }

    extraction1_file = index_dir / "extraction_abc123.json"
    extraction1_file.write_text(json.dumps(extraction1, indent=2))

    # Create database and do initial load
    adapter = SQLiteAdapter(db_path)
    adapter.connect()
    adapter.create_schema()
    adapter.close()

    load_from_extractions(index_dir, verbose=False)

    # Verify initial state
    with SQLiteAdapter(db_path) as adapter:
        books = adapter.fetchall("SELECT title FROM books ORDER BY title")
        assert len(books) == 3
        titles = {book["title"] for book in books}
        assert titles == {"Homegoing", "Mony", "Foundation"}

    # Create extraction with two title changes
    extraction2 = {
        "extraction_metadata": {
            "timestamp": "2024-01-02T00:00:00",
            "git_commit_hash": "def456",
            "git_commit_timestamp": "2024-01-02T00:00:00",
            "extraction_type": "incremental",
            "previous_commit_hash": "abc123",
            "notes_directory": str(tmp_path / "notes"),
        },
        "items": [
            {
                "item_id": "item1",
                "book_title": "Housekeeping",  # Fixed
                "author_first_name": "Marilynne",
                "author_last_name": "Robinson",
                "section": "Introduction",
                "content": "Book A content.",
                "source_file": "bookA.md",
                "line_number": 10,
                "operation": "update",
            },
            {
                "item_id": "item2",
                "book_title": "Money",  # Fixed
                "author_first_name": "Martin",
                "author_last_name": "Amis",
                "section": "Chapter 1",
                "content": "Book B content.",
                "source_file": "bookB.md",
                "line_number": 20,
                "operation": "update",
            },
            # item3 (Foundation) unchanged - not in incremental extraction
        ],
    }

    extraction2_file = index_dir / "extraction_def456.json"
    extraction2_file.write_text(json.dumps(extraction2, indent=2))

    # Run incremental load
    load_incremental(index_dir, verbose=False)

    # Verify final state
    with SQLiteAdapter(db_path) as adapter:
        # Should have only new titles + unchanged book
        books = adapter.fetchall("SELECT title FROM books ORDER BY title")
        assert len(books) == 3, f"Expected 3 books, found {len(books)}"
        titles = {book["title"] for book in books}
        assert titles == {"Housekeeping", "Money", "Foundation"}, f"Wrong titles: {titles}"

        # Old books should be gone
        old_book_a_id = generate_book_id("Homegoing", "Marilynne Robinson")
        old_book_b_id = generate_book_id("Mony", "Martin Amis")

        old_books = adapter.fetchall(
            "SELECT * FROM books WHERE id IN (?, ?)",
            (old_book_a_id, old_book_b_id),
        )
        assert len(old_books) == 0, "Old books should be deleted"

        # No orphaned records
        orphaned_ba = adapter.fetchall(
            """
            SELECT * FROM book_authors
            WHERE book_id NOT IN (SELECT id FROM books)
            """
        )
        assert len(orphaned_ba) == 0, "No orphaned book_authors should exist"

        # All notes should point to correct books
        notes = adapter.fetchall("SELECT item_id, book_id FROM notes ORDER BY item_id")
        assert len(notes) == 3

        expected_mappings = {
            "item1": generate_book_id("Housekeeping", "Marilynne Robinson"),
            "item2": generate_book_id("Money", "Martin Amis"),
            "item3": generate_book_id("Foundation", "Isaac Asimov"),
        }

        for note in notes:
            expected_book_id = expected_mappings[note["item_id"]]
            assert note["book_id"] == expected_book_id, (
                f"Note {note['item_id']} should point to {expected_book_id}, "
                f"but points to {note['book_id']}"
            )


# Example of what the implementation would look like:
"""
def test_book_title_change_cleanup(tmp_db, sample_index):
    from load.db import get_adapter

    # Run incremental load with title change
    load_incremental(sample_index)

    with get_adapter() as adapter:
        # Check that only the new book exists
        books = adapter.fetchall(
            "SELECT id, title FROM books WHERE title LIKE '%keeping%'"
        )

        assert len(books) == 1
        assert books[0]['title'] == 'Housekeeping'

        # Check that old 'Homegoing' by Robinson doesn't exist
        old_books = adapter.fetchall(
            '''
            SELECT b.id, b.title, a.name as author
            FROM books b
            JOIN book_authors ba ON b.id = ba.book_id
            JOIN authors a ON ba.author_id = a.id
            WHERE b.title = 'Homegoing' AND a.name LIKE '%Robinson%'
            '''
        )

        assert len(old_books) == 0

        # Check that notes now point to the new book
        correct_book_id = generate_book_id('Housekeeping', 'Marilynne Robinson')
        notes = adapter.fetchall(
            "SELECT book_id FROM notes WHERE book_id = ?",
            (correct_book_id,)
        )

        assert len(notes) > 0
"""
