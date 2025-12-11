"""Git utilities for incremental extraction."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FileChange:
    """Represents a file change in git."""

    path: Path
    status: Literal["A", "M", "D"]  # Added, Modified, Deleted


def get_current_commit_hash(repo_root: Path) -> str:
    """
    Get current HEAD commit hash.

    Args:
        repo_root: Path to git repository root

    Returns:
        Full commit hash

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_commit_timestamp(repo_root: Path, commit_hash: str) -> str:
    """
    Get ISO timestamp for a commit.

    Args:
        repo_root: Path to git repository root
        commit_hash: Commit hash to query

    Returns:
        ISO formatted timestamp string

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    result = subprocess.run(
        ["git", "show", "-s", "--format=%cI", commit_hash],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def git_diff_files(
    repo_root: Path,
    from_commit: str,
    to_commit: str,
    pattern: str = "*.md",
) -> list[FileChange]:
    """
    Get list of changed files with their change type between two commits.

    Uses: git diff --name-status from_commit..to_commit -- *.md

    Args:
        repo_root: Path to git repository root
        from_commit: Starting commit hash
        to_commit: Ending commit hash (usually "HEAD")
        pattern: File pattern to filter (default: "*.md")

    Returns:
        List of FileChange with status:
        - "A": Added
        - "M": Modified
        - "D": Deleted

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    result = subprocess.run(
        ["git", "diff", "--name-status", f"{from_commit}..{to_commit}", "--", pattern],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    changes: list[FileChange] = []

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        # Format: <status>\t<filepath>
        parts = line.split("\t")
        if len(parts) != 2:
            continue

        status, filepath = parts

        # Handle different status types (A, M, D, R=renamed, C=copied)
        # For renames/copies, we treat them as Modified
        if status.startswith("R") or status.startswith("C"):
            status = "M"
        elif status not in ("A", "M", "D"):
            logger.warning(
                f"Unknown git status '{status}' for file {filepath}, treating as Modified"
            )
            status = "M"

        changes.append(FileChange(path=repo_root / filepath, status=status))  # type: ignore

    return changes


def git_show_file_at_commit(
    repo_root: Path,
    commit_hash: str,
    file_path: Path,
) -> str:
    """
    Get file content at specific commit.

    Uses: git show commit_hash:relative_path

    Args:
        repo_root: Path to git repository root
        commit_hash: Commit hash to query
        file_path: Absolute path to file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist at that commit
        subprocess.CalledProcessError: If git command fails for other reasons
    """
    try:
        # Get relative path from repo root
        rel_path = file_path.relative_to(repo_root)

        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{rel_path}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        # Check if it's a "file not found" error
        if "does not exist" in e.stderr or "Path" in e.stderr:
            raise FileNotFoundError(
                f"File {file_path} does not exist at commit {commit_hash}"
            ) from e
        raise
