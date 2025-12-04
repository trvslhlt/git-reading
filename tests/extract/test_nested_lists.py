"""Tests for nested list handling in extraction."""

import json
import tempfile
from pathlib import Path

from extract.main import parse_markdown_file


def test_nested_lists_grouped_with_parent():
    """Test that nested list items are grouped with their parent note."""
    # Create a test file with nested lists
    content = """# Test Book

## notes
- (p. 10) Parent note with nested content
    - Nested item 1
    - Nested item 2
- (p. 20) Another parent note
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text(content)

        books = parse_markdown_file(test_file, repo_root=None)

        assert len(books) == 1
        book = books[0]

        # Check that notes section has 2 items (not 4)
        assert "notes" in book["sections"]
        notes = book["sections"]["notes"]
        assert len(notes) == 2

        # Check that first note contains nested content
        assert "(p. 10) Parent note with nested content" in notes[0]
        assert "- Nested item 1" in notes[0]
        assert "- Nested item 2" in notes[0]

        # Check that second note is standalone
        assert notes[1] == "(p. 20) Another parent note"


def test_multiple_levels_of_nesting():
    """Test that multiple levels of indentation are preserved."""
    content = """# Test Book

## notes
- Parent note
    - Level 1 nested
        - Level 2 nested
    - Another level 1
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text(content)

        books = parse_markdown_file(test_file, repo_root=None)

        assert len(books) == 1
        notes = books[0]["sections"]["notes"]

        # Should be one item with all nested content
        assert len(notes) == 1
        assert "Parent note" in notes[0]
        assert "- Level 1 nested" in notes[0]
        assert "- Level 2 nested" in notes[0]
        assert "- Another level 1" in notes[0]


def test_non_list_indented_content():
    """Test that indented non-list content is also grouped."""
    content = """# Test Book

## notes
- Parent note with description
    This is a continuation of the parent note
    on multiple lines
- Another note
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text(content)

        books = parse_markdown_file(test_file, repo_root=None)

        notes = books[0]["sections"]["notes"]
        assert len(notes) == 2

        # Check first note contains the indented text
        assert "Parent note with description" in notes[0]
        assert "This is a continuation" in notes[0]
        assert "on multiple lines" in notes[0]
