"""Tests for validation of empty books and sections."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from extract.main import parse_markdown_file


def test_empty_section_logs_error(caplog):
    """Test that sections with no items trigger error logs."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / "author__name.md"

        # Create a markdown file with an empty section
        test_file.write_text(
            """# Test Book

## Notes

## Excerpts
- This has content
"""
        )

        with caplog.at_level(logging.ERROR):
            books = parse_markdown_file(test_file, None)

        # Should still parse the book
        assert len(books) == 1
        assert books[0]["title"] == "Test Book"

        # Should have only the non-empty section
        assert "excerpts" in books[0]["sections"]
        assert "notes" not in books[0]["sections"]

        # Should log error for empty section
        assert "Empty section" in caplog.text
        assert "Test Book" in caplog.text
        assert "Notes" in caplog.text


def test_book_with_no_sections_logs_error(caplog):
    """Test that books with no sections trigger error logs."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / "author__name.md"

        # Create a markdown file with a book but no sections with content
        test_file.write_text(
            """# Book With No Content

Some random text that's not in a section.

# Book With Content

## Notes
- This has content
"""
        )

        with caplog.at_level(logging.ERROR):
            books = parse_markdown_file(test_file, None)

        # Should parse both books
        assert len(books) == 2

        # First book should have no sections
        assert books[0]["title"] == "Book With No Content"
        assert books[0]["sections"] == {}

        # Second book should have sections
        assert books[1]["title"] == "Book With Content"
        assert "notes" in books[1]["sections"]

        # Should log error for book with no sections
        assert "Book with no sections" in caplog.text
        assert "Book With No Content" in caplog.text


def test_multiple_empty_sections_all_logged(caplog):
    """Test that multiple empty sections are all logged."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / "author__name.md"

        # Create a markdown file with multiple empty sections
        test_file.write_text(
            """# Test Book

## Notes

## Excerpts

## Terms

## Ideas
- Only this one has content
"""
        )

        with caplog.at_level(logging.ERROR):
            books = parse_markdown_file(test_file, None)

        # Should parse the book
        assert len(books) == 1
        assert books[0]["title"] == "Test Book"

        # Should have only the section with content
        assert list(books[0]["sections"].keys()) == ["ideas"]

        # Should log error for each empty section
        error_messages = [
            record.message for record in caplog.records if record.levelno == logging.ERROR
        ]
        assert len(error_messages) == 3
        assert any("Notes" in msg for msg in error_messages)
        assert any("Excerpts" in msg for msg in error_messages)
        assert any("Terms" in msg for msg in error_messages)


def test_book_with_only_empty_sections_logs_both_errors(caplog):
    """Test that a book with only empty sections logs both section and book errors."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / "author__name.md"

        # Create a markdown file with a book that has only empty sections
        test_file.write_text(
            """# Empty Book

## Notes

## Excerpts
"""
        )

        with caplog.at_level(logging.ERROR):
            books = parse_markdown_file(test_file, None)

        # Should parse the book
        assert len(books) == 1
        assert books[0]["title"] == "Empty Book"
        assert books[0]["sections"] == {}

        # Should log errors for empty sections AND the empty book
        error_messages = [
            record.message for record in caplog.records if record.levelno == logging.ERROR
        ]
        assert len(error_messages) == 3  # 2 empty sections + 1 empty book

        # Check for section errors
        assert any("Empty section" in msg and "Notes" in msg for msg in error_messages)
        assert any("Empty section" in msg and "Excerpts" in msg for msg in error_messages)

        # Check for book error
        assert any("Book with no sections" in msg and "Empty Book" in msg for msg in error_messages)


def test_valid_book_no_errors(caplog):
    """Test that valid books with content don't trigger errors."""
    with TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        test_file = tmpdir_path / "author__name.md"

        # Create a valid markdown file
        test_file.write_text(
            """# Valid Book

## Notes
- Note 1
- Note 2

## Excerpts
- Quote 1
"""
        )

        with caplog.at_level(logging.ERROR):
            books = parse_markdown_file(test_file, None)

        # Should parse the book
        assert len(books) == 1
        assert books[0]["title"] == "Valid Book"
        assert "notes" in books[0]["sections"]
        assert "excerpts" in books[0]["sections"]

        # Should not log any errors
        error_messages = [
            record.message for record in caplog.records if record.levelno == logging.ERROR
        ]
        assert len(error_messages) == 0
