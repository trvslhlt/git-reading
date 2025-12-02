"""Data models for repository content and history."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Sequence


@dataclass
class FileSnapshot:
    """Represents the current contents of a repository file."""

    path: Path
    content: str

    def lines(self) -> Sequence[str]:
        """Return the file content split into logical lines."""
        return self.content.splitlines()


@dataclass
class CommitChange:
    """Minimal summary of a change introduced in a commit for a file."""

    file_path: Path
    patch: str


@dataclass
class CommitInfo:
    """Metadata for a single commit in the repository history."""

    sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    summary: str
    changes: List[CommitChange] = field(default_factory=list)


@dataclass
class RepositorySnapshot:
    """Single structure bundling the current state and recent history."""

    root: Path
    files: List[FileSnapshot]
    commits: List[CommitInfo]


@dataclass
class AnswerCandidate:
    """Represents a snippet surfaced as a potential answer."""

    score: float
    source: str
    location: str
    excerpt: str
