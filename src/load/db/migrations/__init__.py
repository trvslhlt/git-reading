"""Database migration system for git-reading.

This module provides a simple migration system that tracks schema versions
and applies migrations automatically.
"""

from .runner import MigrationRunner

__all__ = ["MigrationRunner"]
