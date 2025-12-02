"""Thin wrappers around git commands."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List


class GitError(RuntimeError):
    """Raised when a git command fails."""


def _run_git(args: Iterable[str], *, cwd: Path) -> str:
    """Run a git sub-command and return stripped stdout."""
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise GitError(completed.stderr.strip() or "git command failed")
    return completed.stdout


def get_tracked_files(root: Path) -> List[Path]:
    """Return tracked file paths relative to ``root``."""
    output = _run_git(["ls-files"], cwd=root)
    return [root / line.strip() for line in output.splitlines() if line.strip()]


def get_commit_log(root: Path, *, max_count: int = 50) -> str:
    """Return raw git log output for the repository."""
    format_args = [
        "log",
        f"-n{max_count}",
        "--date=iso-strict",
        "--pretty=format:%x1e%H%x1f%an%x1f%ae%x1f%ad%x1f%s",
        "--patch",
    ]
    return _run_git(format_args, cwd=root)
