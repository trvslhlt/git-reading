"""High level repository scanning utilities."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .git_tools import get_commit_log, get_tracked_files
from .models import CommitChange, CommitInfo, FileSnapshot, RepositorySnapshot


_DIFF_HEADER = re.compile(r"^diff --git a/(.*?) b/(.*?)$")
_MAX_PATCH_CHARS = 10_000


def load_repository_snapshot(
    root: Path,
    *,
    max_commits: int = 50,
    max_file_bytes: int = 200_000,
) -> RepositorySnapshot:
    """Collect the current contents and recent history for ``root``."""
    files = _load_files(root, max_file_bytes=max_file_bytes)
    commits = _load_commits(root, max_commits=max_commits)
    return RepositorySnapshot(root=root, files=files, commits=commits)


def _load_files(root: Path, *, max_file_bytes: int) -> List[FileSnapshot]:
    """Load a snapshot for each tracked file."""
    snapshots: List[FileSnapshot] = []
    for file_path in get_tracked_files(root):
        if not file_path.exists():
            continue
        try:
            data = file_path.read_bytes()
        except OSError:
            continue
        if len(data) > max_file_bytes:
            data = data[:max_file_bytes]
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="ignore")
        snapshots.append(FileSnapshot(path=file_path.relative_to(root), content=text))
    return snapshots


def _load_commits(root: Path, *, max_commits: int) -> List[CommitInfo]:
    """Parse commit metadata and minimal patch details."""
    raw_log = get_commit_log(root, max_count=max_commits)
    commits: List[CommitInfo] = []
    for segment in raw_log.split("\x1e"):
        segment = segment.strip()
        if not segment:
            continue
        lines = segment.splitlines()
        header = lines[0]
        patch_lines = lines[1:]
        parts = header.split("\x1f")
        if len(parts) != 5:
            continue
        sha, author_name, author_email, authored_at, summary = parts
        commit = CommitInfo(
            sha=sha,
            author_name=author_name,
            author_email=author_email,
            authored_at=datetime.fromisoformat(authored_at),
            summary=summary,
            changes=_parse_changes(patch_lines),
        )
        commits.append(commit)
    return commits


def _parse_changes(patch_lines: Iterable[str]) -> List[CommitChange]:
    """Split a combined patch into per-file patches."""
    changes: List[CommitChange] = []
    current_path: Path | None = None
    current_patch: List[str] = []
    for line in patch_lines:
        match = _DIFF_HEADER.match(line)
        if match:
            if current_path is not None and current_patch:
                changes.append(
                    CommitChange(
                        file_path=current_path,
                        patch=_truncate_patch("\n".join(current_patch)),
                    )
                )
            current_patch = []
            current_path = Path(match.group(2))
            continue
        if current_path is not None:
            current_patch.append(line)
    if current_path is not None and current_patch:
        changes.append(
            CommitChange(
                file_path=current_path,
                patch=_truncate_patch("\n".join(current_patch)),
            )
        )
    return changes


def _truncate_patch(patch: str) -> str:
    if len(patch) <= _MAX_PATCH_CHARS:
        return patch.strip()
    return patch[: _MAX_PATCH_CHARS].rstrip() + "\n… (truncated)"
