"""Data models for incremental extraction."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class ExtractionMetadata:
    """Metadata about an extraction run."""

    timestamp: str
    git_commit_hash: str
    git_commit_timestamp: str
    extraction_type: Literal["full", "incremental"]
    previous_commit_hash: str | None
    notes_directory: str


@dataclass
class ExtractedItem:
    """A single extracted item (note or excerpt) with metadata."""

    item_id: str
    operation: Literal["add", "update", "delete"]
    book_title: str
    author_first_name: str
    author_last_name: str
    section: str
    content: str
    source_file: str
    date_read: str | None


@dataclass
class ExtractionFile:
    """Complete extraction file structure."""

    extraction_metadata: ExtractionMetadata
    items: list[ExtractedItem]
