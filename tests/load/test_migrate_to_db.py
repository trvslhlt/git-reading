"""Integration tests for database migration."""

import json
import sqlite3
from pathlib import Path

import pytest

from load.db_schema import create_database
from load.migrate_to_db import migrate_from_json, verify_migration


@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file with test data."""

    def _create_json(books_data):
        json_path = tmp_path / "test_index.json"
        data = {"books": books_data, "total_books": len(books_data)}
        with open(json_path, "w") as f:
            json.dump(data, f)
        return json_path

    return _create_json


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test.db"


class TestMigrateFromJson:
    """Tests for migrate_from_json function."""

    def test_full_migration_with_author_fields(self, temp_json_file, temp_db_path):
        """Test full migration with author_first_name and author_last_name."""
        books = [
            {
                "title": "Test Book",
                "author_first_name": "John",
                "author_last_name": "Doe",
                "date_read": "2024-01-15",
                "source_file": "doe__john.md",
                "sections": {
                    "notes": ["Note 1", "Note 2"],
                    "excerpts": ["Quote 1"],
                },
            }
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        # Verify database contents
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check authors table
        cursor.execute("SELECT first_name, last_name, name FROM authors")
        authors = cursor.fetchall()
        assert len(authors) == 1
        assert authors[0] == ("John", "Doe", "John Doe")

        # Check books table
        cursor.execute("SELECT title FROM books")
        books_result = cursor.fetchall()
        assert len(books_result) == 1
        assert books_result[0][0] == "Test Book"

        # Check chunks table
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        assert chunk_count == 3  # 2 notes + 1 excerpt

        conn.close()

    def test_migration_only_last_name(self, temp_json_file, temp_db_path):
        """Test migration with only last name (empty first name)."""
        books = [
            {
                "title": "Book",
                "author_first_name": "",
                "author_last_name": "Smith",
                "sections": {"notes": ["Note 1"]},
            }
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT first_name, last_name, name FROM authors")
        author = cursor.fetchone()
        assert author == ("", "Smith", "Smith")

        conn.close()

    def test_migration_only_first_name(self, temp_json_file, temp_db_path):
        """Test migration with only first name (empty last name)."""
        books = [
            {
                "title": "Book",
                "author_first_name": "Jane",
                "author_last_name": "",
                "sections": {"notes": ["Note 1"]},
            }
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT first_name, last_name, name FROM authors")
        author = cursor.fetchone()
        assert author == ("Jane", "", "Jane")

        conn.close()

    def test_migration_unknown_author(self, temp_json_file, temp_db_path):
        """Test migration with empty author names."""
        books = [
            {
                "title": "Book",
                "author_first_name": "",
                "author_last_name": "",
                "sections": {"notes": ["Note 1"]},
            }
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT first_name, last_name, name FROM authors")
        author = cursor.fetchone()
        assert author == ("", "", "Unknown")

        conn.close()

    def test_migration_same_author_multiple_books(self, temp_json_file, temp_db_path):
        """Test that same author is reused for multiple books."""
        books = [
            {
                "title": "Book 1",
                "author_first_name": "John",
                "author_last_name": "Doe",
                "sections": {"notes": ["Note 1"]},
            },
            {
                "title": "Book 2",
                "author_first_name": "John",
                "author_last_name": "Doe",
                "sections": {"notes": ["Note 2"]},
            },
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Should only have one author
        cursor.execute("SELECT COUNT(*) FROM authors")
        author_count = cursor.fetchone()[0]
        assert author_count == 1

        # Should have two books
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        assert book_count == 2

        # Both books should link to same author
        cursor.execute(
            """
            SELECT COUNT(DISTINCT author_id)
            FROM book_authors
        """
        )
        distinct_authors = cursor.fetchone()[0]
        assert distinct_authors == 1

        conn.close()

    def test_migration_multiple_sections(self, temp_json_file, temp_db_path):
        """Test migration with multiple section types."""
        books = [
            {
                "title": "Book",
                "author_first_name": "Jane",
                "author_last_name": "Smith",
                "sections": {
                    "notes": ["Note 1", "Note 2"],
                    "excerpts": ["Quote 1", "Quote 2", "Quote 3"],
                    "threads": ["Thread 1"],
                },
            }
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check chunks by section
        cursor.execute("SELECT section, COUNT(*) FROM chunks GROUP BY section")
        sections = dict(cursor.fetchall())

        assert sections["notes"] == 2
        assert sections["excerpts"] == 3
        assert sections["threads"] == 1

        conn.close()

    def test_migration_faiss_indices_sequential(self, temp_json_file, temp_db_path):
        """Test that FAISS indices are sequential starting from 0."""
        books = [
            {
                "title": "Book 1",
                "author_first_name": "Author",
                "author_last_name": "One",
                "sections": {"notes": ["Note 1", "Note 2"]},
            },
            {
                "title": "Book 2",
                "author_first_name": "Author",
                "author_last_name": "Two",
                "sections": {"excerpts": ["Quote 1", "Quote 2", "Quote 3"]},
            },
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT faiss_index FROM chunks ORDER BY faiss_index")
        indices = [row[0] for row in cursor.fetchall()]

        # Should be 0, 1, 2, 3, 4
        assert indices == list(range(len(indices)))

        conn.close()

    def test_migration_empty_sections(self, temp_json_file, temp_db_path):
        """Test migration with empty sections list.

        Note: Current implementation only creates books/authors when chunks exist.
        Books with no content are not migrated to the database.
        """
        books = [
            {
                "title": "Book",
                "author_first_name": "John",
                "author_last_name": "Doe",
                "sections": {"notes": []},
            }
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # With no chunks, no books or authors are created
        cursor.execute("SELECT COUNT(*) FROM books")
        assert cursor.fetchone()[0] == 0

        cursor.execute("SELECT COUNT(*) FROM authors")
        assert cursor.fetchone()[0] == 0

        cursor.execute("SELECT COUNT(*) FROM chunks")
        assert cursor.fetchone()[0] == 0

        conn.close()


class TestVerifyMigration:
    """Tests for verify_migration function."""

    def test_verify_successful_migration(self, temp_json_file, temp_db_path):
        """Test that verification passes for successful migration."""
        books = [
            {
                "title": "Book",
                "author_first_name": "John",
                "author_last_name": "Doe",
                "sections": {
                    "notes": ["Note 1", "Note 2"],
                    "excerpts": ["Quote 1"],
                },
            }
        ]

        json_path = temp_json_file(books)
        migrate_from_json(json_path, temp_db_path, verbose=False)

        # Verification should pass
        result = verify_migration(temp_db_path, json_path)
        assert result is True

    def test_verify_detects_missing_chunks(self, temp_json_file, temp_db_path):
        """Test that verification detects if chunks are missing."""
        books = [
            {
                "title": "Book",
                "author_first_name": "John",
                "author_last_name": "Doe",
                "sections": {"notes": ["Note 1", "Note 2"]},
            }
        ]

        json_path = temp_json_file(books)

        # Create database but manually insert fewer chunks
        create_database(temp_db_path)
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Insert author
        cursor.execute(
            "INSERT INTO authors (id, first_name, last_name, name) VALUES (?, ?, ?, ?)",
            ("john-doe", "John", "Doe", "John Doe"),
        )

        # Insert book
        cursor.execute(
            "INSERT INTO books (id, title) VALUES (?, ?)",
            ("book-john-doe", "Book"),
        )

        # Link book to author
        cursor.execute(
            "INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)",
            ("book-john-doe", "john-doe"),
        )

        # Only insert 1 chunk instead of 2
        cursor.execute(
            "INSERT INTO chunks (book_id, section, excerpt, faiss_index) VALUES (?, ?, ?, ?)",
            ("book-john-doe", "notes", "Note 1", 0),
        )

        conn.commit()
        conn.close()

        # Verification should fail
        result = verify_migration(temp_db_path, json_path)
        assert result is False
