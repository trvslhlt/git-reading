"""
Integration tests for incremental extraction.

These tests create temporary git repositories, make changes across commits,
and verify that incremental extraction correctly detects adds/updates/deletes.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from extract.main import extract_full, extract_incremental


@pytest.fixture
def temp_git_repo(tmp_path):
    """
    Create a temporary git repository with proper git config.
    Returns the repo path.
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


def git_commit_all(repo_path, message="commit"):
    """Add all changes and commit."""
    subprocess.run(
        ["git", "add", "."],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )


def read_extraction_file(file_path: Path) -> dict:
    """Read and parse extraction JSON file."""
    with open(file_path) as f:
        return json.load(f)


def test_first_run_full_extraction(temp_git_repo):
    """Test that first run performs full extraction."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Create initial markdown file
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 2

## Excerpts
- Quote 1
""")

    git_commit_all(repo_path, "Add first book")

    # Run incremental extraction (should detect no previous and do full)
    result = extract_incremental(notes_dir, index_dir, repo_path)

    assert result is not None
    assert result.exists()

    # Verify extraction file
    data = read_extraction_file(result)
    assert data["extraction_metadata"]["extraction_type"] == "full"
    assert data["extraction_metadata"]["previous_commit_hash"] is None
    assert len(data["items"]) == 3  # 2 notes + 1 excerpt
    assert all(item["operation"] == "add" for item in data["items"])


def test_no_changes_skips_extraction(temp_git_repo):
    """Test that running again with no changes skips extraction."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Create and commit initial file
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
""")
    git_commit_all(repo_path, "Initial")

    # First extraction
    extract_incremental(notes_dir, index_dir, repo_path)

    # Second extraction with no changes
    result = extract_incremental(notes_dir, index_dir, repo_path)

    assert result is None  # No extraction file created


def test_added_file(temp_git_repo):
    """Test detecting a new markdown file."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Initial state
    (notes_dir / "author1__john.md").write_text("""# Book One

## Notes
- Note 1
""")
    git_commit_all(repo_path, "Initial")

    # First extraction
    extract_incremental(notes_dir, index_dir, repo_path)

    # Add new file
    (notes_dir / "author2__jane.md").write_text("""# Book Two

## Notes
- Note A
- Note B
""")
    git_commit_all(repo_path, "Add second book")

    # Incremental extraction
    result = extract_incremental(notes_dir, index_dir, repo_path)

    assert result is not None
    data = read_extraction_file(result)
    assert data["extraction_metadata"]["extraction_type"] == "incremental"
    assert len(data["items"]) == 2  # 2 new notes
    assert all(item["operation"] == "add" for item in data["items"])
    assert all(item["source_file"] == "author2__jane.md" for item in data["items"])


def test_modified_file_add_notes(temp_git_repo):
    """Test detecting added notes in existing file."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Initial state
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
""")
    git_commit_all(repo_path, "Initial")

    extract_incremental(notes_dir, index_dir, repo_path)

    # Add more notes
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 2
- Note 3
""")
    git_commit_all(repo_path, "Add notes")

    # Incremental extraction
    result = extract_incremental(notes_dir, index_dir, repo_path)

    data = read_extraction_file(result)
    assert len(data["items"]) == 2  # 2 new notes
    assert all(item["operation"] == "add" for item in data["items"])
    assert {item["content"] for item in data["items"]} == {"Note 2", "Note 3"}


def test_modified_file_delete_notes(temp_git_repo):
    """Test detecting deleted notes in existing file."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Initial state with 3 notes
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 2
- Note 3
""")
    git_commit_all(repo_path, "Initial")

    extract_incremental(notes_dir, index_dir, repo_path)

    # Remove one note
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 3
""")
    git_commit_all(repo_path, "Remove note")

    # Incremental extraction
    result = extract_incremental(notes_dir, index_dir, repo_path)

    data = read_extraction_file(result)
    assert len(data["items"]) == 1  # 1 deleted note
    assert data["items"][0]["operation"] == "delete"
    assert data["items"][0]["content"] == "Note 2"


def test_deleted_file(temp_git_repo):
    """Test detecting a deleted markdown file."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Initial state with two files
    (notes_dir / "author1__john.md").write_text("""# Book One

## Notes
- Note 1
""")
    (notes_dir / "author2__jane.md").write_text("""# Book Two

## Notes
- Note A
- Note B
""")
    git_commit_all(repo_path, "Initial")

    extract_incremental(notes_dir, index_dir, repo_path)

    # Delete second file
    (notes_dir / "author2__jane.md").unlink()
    git_commit_all(repo_path, "Delete file")

    # Incremental extraction
    result = extract_incremental(notes_dir, index_dir, repo_path)

    data = read_extraction_file(result)
    assert len(data["items"]) == 2  # 2 deleted notes
    assert all(item["operation"] == "delete" for item in data["items"])
    assert all(item["source_file"] == "author2__jane.md" for item in data["items"])


def test_mixed_operations(temp_git_repo):
    """Test multiple operation types in single extraction."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Initial state
    (notes_dir / "author1__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 2
""")
    (notes_dir / "author2__jane.md").write_text("""# Book Two

## Notes
- Note A
""")
    git_commit_all(repo_path, "Initial")

    extract_incremental(notes_dir, index_dir, repo_path)

    # Make various changes
    # File 1: Add and delete notes
    (notes_dir / "author1__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 3
""")
    # File 2: Delete completely
    (notes_dir / "author2__jane.md").unlink()
    # File 3: Add new file
    (notes_dir / "author3__bob.md").write_text("""# Book Three

## Notes
- Note X
""")
    git_commit_all(repo_path, "Mixed changes")

    # Incremental extraction
    result = extract_incremental(notes_dir, index_dir, repo_path)

    data = read_extraction_file(result)

    # Count operations
    adds = [item for item in data["items"] if item["operation"] == "add"]
    deletes = [item for item in data["items"] if item["operation"] == "delete"]

    assert len(adds) == 2  # Note 3 + Note X
    assert len(deletes) == 2  # Note 2 + Note A


def test_multiple_incremental_runs(temp_git_repo):
    """Test sequence of incremental extractions."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # First commit
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
""")
    git_commit_all(repo_path, "Commit 1")
    result1 = extract_incremental(notes_dir, index_dir, repo_path)
    assert result1 is not None

    # Second commit
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 2
""")
    git_commit_all(repo_path, "Commit 2")
    result2 = extract_incremental(notes_dir, index_dir, repo_path)
    assert result2 is not None

    # Third commit
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
- Note 2
- Note 3
""")
    git_commit_all(repo_path, "Commit 3")
    result3 = extract_incremental(notes_dir, index_dir, repo_path)
    assert result3 is not None

    # Verify all three extraction files exist
    assert len(list(index_dir.glob("extraction_*.json"))) == 3

    # Verify second extraction references first
    data2 = read_extraction_file(result2)
    data1 = read_extraction_file(result1)
    assert (
        data2["extraction_metadata"]["previous_commit_hash"]
        == data1["extraction_metadata"]["git_commit_hash"]
    )


def test_full_flag_forces_full_extraction(temp_git_repo):
    """Test that --full flag forces full extraction in fresh directory."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Initial state
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
""")
    git_commit_all(repo_path, "Initial")

    # First extraction (incremental, becomes full)
    extract_incremental(notes_dir, index_dir, repo_path)

    # Force full extraction in a NEW directory (required for full extraction)
    index_dir2 = repo_path / "index_full"
    result = extract_full(notes_dir, index_dir2, repo_path)

    data = read_extraction_file(result)
    assert data["extraction_metadata"]["extraction_type"] == "full"
    assert data["extraction_metadata"]["previous_commit_hash"] is None
    assert all(item["operation"] == "add" for item in data["items"])


def test_item_id_consistency(temp_git_repo):
    """Test that same content generates same item ID."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Create initial file
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Consistent Note
""")
    git_commit_all(repo_path, "Initial")

    result1 = extract_full(notes_dir, index_dir, repo_path)
    data1 = read_extraction_file(result1)
    item_id1 = data1["items"][0]["item_id"]

    # Create in different directory for second extraction
    index_dir2 = repo_path / "index2"

    # Delete and recreate same content
    (notes_dir / "author__john.md").write_text("")
    git_commit_all(repo_path, "Delete")

    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Consistent Note
""")
    git_commit_all(repo_path, "Recreate")

    result2 = extract_full(notes_dir, index_dir2, repo_path)
    data2 = read_extraction_file(result2)
    item_id2 = data2["items"][0]["item_id"]

    # Same content should produce same ID
    assert item_id1 == item_id2


def test_full_extraction_fails_with_existing_files(temp_git_repo):
    """Test that full extraction fails if index directory has existing files."""
    repo_path = temp_git_repo
    notes_dir = repo_path / "notes"
    notes_dir.mkdir()
    index_dir = repo_path / "index"

    # Create initial file
    (notes_dir / "author__john.md").write_text("""# Book One

## Notes
- Note 1
""")
    git_commit_all(repo_path, "Initial")

    # First extraction succeeds
    extract_full(notes_dir, index_dir, repo_path)

    # Second full extraction should fail
    with pytest.raises(ValueError, match="already contains.*extraction file"):
        extract_full(notes_dir, index_dir, repo_path)
