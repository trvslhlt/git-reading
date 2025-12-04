"""
Integration tests for index_readings.

These tests create temporary git repositories with markdown files,
commit them with specific dates, and verify the indexing works correctly.
"""

import json
import subprocess
from datetime import datetime

import pytest

from extract.main import index_notes


@pytest.fixture
def temp_git_repo(tmp_path):
    """
    Create a temporary git repository with proper git config.

    Returns a tuple of (repo_path, notes_path) where notes can be
    stored in a subdirectory if needed.
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


def git_commit_file(repo_path, file_path, commit_date=None):
    """
    Add and commit a file with an optional date.

    Args:
        repo_path: Path to git repository
        file_path: Path to file (relative to repo_path or absolute)
        commit_date: ISO date string (e.g., "2024-01-15") or None for current time
    """
    rel_path = file_path.relative_to(repo_path) if file_path.is_absolute() else file_path

    subprocess.run(
        ["git", "add", str(rel_path)],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    env = None
    if commit_date:
        # Convert date to git's expected format
        dt = datetime.fromisoformat(commit_date)
        git_date = dt.strftime("%Y-%m-%d %H:%M:%S")
        env = {
            "GIT_AUTHOR_DATE": git_date,
            "GIT_COMMITTER_DATE": git_date,
        }

    subprocess.run(
        ["git", "commit", "-m", f"Add {rel_path}"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        env=env,
    )


def test_basic_indexing_same_directory(temp_git_repo):
    """Test indexing when notes and git repo are in the same directory."""
    repo_path = temp_git_repo

    # Create a markdown file with book notes
    notes_file = repo_path / "author__john.md"
    notes_file.write_text("""# The Great Book

## Notes
- First note
- Second note

## Excerpts
- Great quote here
""")

    # Commit the file with a specific date
    git_commit_file(repo_path, notes_file, "2024-03-15")

    # Run the indexer
    output_path = repo_path / "index.json"
    index_notes(repo_path, output_path)

    # Verify the output
    assert output_path.exists()
    index = json.loads(output_path.read_text())

    assert index["total_books"] == 1
    assert len(index["books"]) == 1

    book = index["books"][0]
    assert book["title"] == "The Great Book"
    assert book["author"] == "John Author"
    assert book["date_read"] == "2024-03-15"
    assert book["source_file"] == "author__john.md"
    assert "notes" in book["sections"]
    assert book["sections"]["notes"] == ["First note", "Second note"]
    assert book["sections"]["excerpts"] == ["Great quote here"]


def test_indexing_separate_directories(temp_git_repo):
    """Test indexing when notes are in a subdirectory of the git repo."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "reading_notes"
    notes_dir.mkdir()

    # Create a markdown file in the subdirectory
    notes_file = notes_dir / "smith__jane.md"
    notes_file.write_text("""# Book One

## Threads
- Main theme

# Book Two

## Notes
- Important point
""")

    # Commit the file
    git_commit_file(repo_path, notes_file, "2024-06-20")

    # Run the indexer with separate directories
    output_path = repo_path / "books.json"
    index_notes(notes_dir, output_path, repo_path)

    # Verify the output
    assert output_path.exists()
    index = json.loads(output_path.read_text())

    assert index["total_books"] == 2

    # Books should be sorted by date
    assert index["books"][0]["title"] == "Book One"
    assert index["books"][0]["date_read"] == "2024-06-20"
    assert index["books"][0]["author"] == "Jane Smith"

    assert index["books"][1]["title"] == "Book Two"
    assert index["books"][1]["date_read"] == "2024-06-20"


def test_multiple_books_different_dates(temp_git_repo):
    """Test that books added at different times get different dates."""
    repo_path = temp_git_repo

    # Create initial file with first book
    notes_file = repo_path / "author_test.md"
    notes_file.write_text("""# First Book

## Notes
- Note one
""")
    git_commit_file(repo_path, notes_file, "2024-01-10")

    # Add second book to the same file
    notes_file.write_text("""# First Book

## Notes
- Note one

# Second Book

## Notes
- Note two
""")
    git_commit_file(repo_path, notes_file, "2024-02-15")

    # Add third book
    notes_file.write_text("""# First Book

## Notes
- Note one

# Second Book

## Notes
- Note two

# Third Book

## Notes
- Note three
""")
    git_commit_file(repo_path, notes_file, "2024-03-20")

    # Run the indexer
    output_path = repo_path / "index.json"
    index_notes(repo_path, output_path)

    # Verify dates
    index = json.loads(output_path.read_text())
    assert index["total_books"] == 3

    # Books should be sorted by date
    assert index["books"][0]["title"] == "First Book"
    assert index["books"][0]["date_read"] == "2024-01-10"

    assert index["books"][1]["title"] == "Second Book"
    assert index["books"][1]["date_read"] == "2024-02-15"

    assert index["books"][2]["title"] == "Third Book"
    assert index["books"][2]["date_read"] == "2024-03-20"


def test_no_git_repository(tmp_path):
    """Test that indexing works without git (no dates)."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    notes_file = notes_dir / "author_name.md"
    notes_file.write_text("""# Some Book

## Notes
- A note
""")

    output_path = tmp_path / "index.json"
    index_notes(notes_dir, output_path)

    index = json.loads(output_path.read_text())
    assert index["total_books"] == 1
    assert index["books"][0]["date_read"] is None


def test_multiple_authors(temp_git_repo):
    """Test indexing multiple markdown files for different authors."""
    repo_path = temp_git_repo

    # Create files for different authors
    file1 = repo_path / "barth__john.md"
    file1.write_text("""# Lost in the Funhouse

## Excerpts
- Quote here
""")
    git_commit_file(repo_path, file1, "2024-04-01")

    file2 = repo_path / "pynchon__thomas.md"
    file2.write_text("""# Gravity's Rainbow

## Notes
- Complex novel
""")
    git_commit_file(repo_path, file2, "2024-05-01")

    # Run the indexer
    output_path = repo_path / "index.json"
    index_notes(repo_path, output_path)

    index = json.loads(output_path.read_text())
    assert index["total_books"] == 2

    # Verify authors were parsed correctly from filenames
    authors = {book["author"] for book in index["books"]}
    assert authors == {"John Barth", "Thomas Pynchon"}
