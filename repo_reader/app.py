"""User-facing facade that ties together scanning and Q&A."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from .models import AnswerCandidate, RepositorySnapshot
from .qa import RepositoryIndex
from .scanner import load_repository_snapshot


class RepositoryQAApp:
    """Loads a repository and answers keyword-style questions about it."""

    def __init__(
        self,
        root: Path | str,
        *,
        max_commits: int = 50,
        max_file_bytes: int = 200_000,
    ) -> None:
        self.root = Path(root)
        self.max_commits = max_commits
        self.max_file_bytes = max_file_bytes
        self._snapshot: Optional[RepositorySnapshot] = None
        self._index: Optional[RepositoryIndex] = None

    @property
    def snapshot(self) -> RepositorySnapshot:
        if self._snapshot is None:
            raise RuntimeError("Repository snapshot not loaded")
        return self._snapshot

    def build(self) -> None:
        """Read repository state and prepare the search index."""
        snapshot = load_repository_snapshot(
            self.root,
            max_commits=self.max_commits,
            max_file_bytes=self.max_file_bytes,
        )
        self._snapshot = snapshot
        self._index = RepositoryIndex(snapshot)

    def ask(self, question: str, *, limit: int = 5) -> List[AnswerCandidate]:
        """Return candidate excerpts relevant to the supplied question."""
        if self._index is None:
            raise RuntimeError("Call build() before querying")
        return self._index.query(question, limit=limit)

    def summarize(self) -> str:
        """Return a simple textual summary of the repository."""
        snapshot = self.snapshot
        file_count = len(snapshot.files)
        commit_count = len(snapshot.commits)
        lines = [
            f"Repository: {snapshot.root}",
            f"Tracked files loaded: {file_count}",
            f"Recent commits loaded: {commit_count}",
        ]
        if snapshot.commits:
            recent = snapshot.commits[0]
            lines.append(
                "Most recent commit: "
                f"{recent.sha[:7]} by {recent.author_name} on {recent.authored_at:%Y-%m-%d}"  # noqa: E501
            )
        return "\n".join(lines)

    def recent_commit_summaries(self, *, limit: int = 5) -> Iterable[str]:
        snapshot = self.snapshot
        for commit in snapshot.commits[:limit]:
            yield f"{commit.sha[:7]} {commit.summary}"
