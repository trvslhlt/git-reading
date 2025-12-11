"""Extraction file I/O utilities."""

import json
from pathlib import Path

from .file_utils import find_latest_extraction
from .models import ExtractedItem, ExtractionFile, ExtractionMetadata


def write_extraction_file(
    file_path: Path,
    metadata: ExtractionMetadata,
    items: list[ExtractedItem],
) -> None:
    """
    Write extraction file with proper formatting.

    Args:
        file_path: Path to write the file
        metadata: Extraction metadata
        items: List of extracted items
    """
    # Convert to dict structure
    data = {
        "extraction_metadata": {
            "timestamp": metadata.timestamp,
            "git_commit_hash": metadata.git_commit_hash,
            "git_commit_timestamp": metadata.git_commit_timestamp,
            "extraction_type": metadata.extraction_type,
            "previous_commit_hash": metadata.previous_commit_hash,
            "notes_directory": metadata.notes_directory,
        },
        "items": [
            {
                "item_id": item.item_id,
                "operation": item.operation,
                "book_title": item.book_title,
                "author_first_name": item.author_first_name,
                "author_last_name": item.author_last_name,
                "section": item.section,
                "content": item.content,
                "source_file": item.source_file,
                "date_read": item.date_read,
            }
            for item in items
        ],
    }

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with pretty formatting
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_extraction_file(file_path: Path) -> ExtractionFile:
    """
    Read and parse extraction file.

    Args:
        file_path: Path to the extraction file

    Returns:
        ExtractionFile object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Extraction file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)

    # Parse metadata
    metadata_dict = data.get("extraction_metadata", {})
    metadata = ExtractionMetadata(
        timestamp=metadata_dict["timestamp"],
        git_commit_hash=metadata_dict["git_commit_hash"],
        git_commit_timestamp=metadata_dict["git_commit_timestamp"],
        extraction_type=metadata_dict["extraction_type"],
        previous_commit_hash=metadata_dict.get("previous_commit_hash"),
        notes_directory=metadata_dict["notes_directory"],
    )

    # Parse items
    items_list = data.get("items", [])
    items = [
        ExtractedItem(
            item_id=item["item_id"],
            operation=item["operation"],
            book_title=item["book_title"],
            author_first_name=item["author_first_name"],
            author_last_name=item["author_last_name"],
            section=item["section"],
            content=item["content"],
            source_file=item["source_file"],
            date_read=item.get("date_read"),
        )
        for item in items_list
    ]

    return ExtractionFile(extraction_metadata=metadata, items=items)


def read_previous_commit_hash(index_dir: Path) -> str | None:
    """
    Read the most recent extraction file and return its commit hash.

    Args:
        index_dir: Directory containing extraction files

    Returns:
        Commit hash from most recent extraction, or None if no extractions exist
    """
    latest_file = find_latest_extraction(index_dir)

    if latest_file is None:
        return None

    try:
        extraction = read_extraction_file(latest_file)
        return extraction.extraction_metadata.git_commit_hash
    except (FileNotFoundError, ValueError, KeyError):
        return None
