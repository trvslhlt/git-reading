"""Utilities for replaying extraction files to reconstruct state."""

from collections import defaultdict
from pathlib import Path

from .extraction_io import read_extraction_file
from .file_utils import find_latest_extraction, list_extractions_chronological
from .models import ExtractedItem, ExtractionFile


def get_latest_extraction(index_dir: Path) -> ExtractionFile | None:
    """
    Get the most recent extraction file.

    Args:
        index_dir: Directory containing extraction files

    Returns:
        ExtractionFile or None if no extractions found
    """
    latest_path = find_latest_extraction(index_dir)
    if not latest_path:
        return None
    return read_extraction_file(latest_path)


def get_new_extractions_since(index_dir: Path, last_processed_commit: str) -> list[ExtractionFile]:
    """
    Get all extraction files after a specific commit.

    Returns extractions in chronological order, starting AFTER last_processed_commit.
    Consumers track which commit they last processed, then get only new changes.

    Args:
        index_dir: Directory containing extraction files
        last_processed_commit: Git commit hash of last processed extraction

    Returns:
        List of ExtractionFile objects in chronological order
    """
    all_extractions = []
    found_checkpoint = False

    for path in list_extractions_chronological(index_dir):
        extraction = read_extraction_file(path)

        # Skip until we find the last processed commit
        if extraction.extraction_metadata.git_commit_hash == last_processed_commit:
            found_checkpoint = True
            continue

        # Only include extractions after the checkpoint
        if found_checkpoint:
            all_extractions.append(extraction)

    return all_extractions


def replay_all_extractions(index_dir: Path) -> list[ExtractedItem]:
    """
    Replay ALL extraction files to get full current state.

    Use this for initial load or full rebuild.
    Applies all operations (add/update/delete) in chronological order
    to reconstruct the current state.

    Args:
        index_dir: Directory containing extraction files

    Returns:
        Flat list of current items (after applying all operations)
    """
    state: dict[str, ExtractedItem] = {}

    for extraction_path in list_extractions_chronological(index_dir):
        extraction = read_extraction_file(extraction_path)

        for item in extraction.items:
            if item.operation == "add":
                state[item.item_id] = item
            elif item.operation == "update":
                state[item.item_id] = item
            elif item.operation == "delete":
                state.pop(item.item_id, None)

    return list(state.values())


def group_items_by_book(
    items: list[ExtractedItem],
) -> dict[tuple[str, str, str], list[ExtractedItem]]:
    """
    Group items by (book_title, author_first_name, author_last_name).

    Helper for consumers that need book-centric view (e.g., analytics dashboard).

    Args:
        items: Flat list of extracted items

    Returns:
        Dict mapping (book_title, first_name, last_name) to list of items
    """
    books = defaultdict(list)
    for item in items:
        key = (item.book_title, item.author_first_name, item.author_last_name)
        books[key].append(item)

    return dict(books)
