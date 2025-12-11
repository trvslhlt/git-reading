"""Utilities for extraction file naming and discovery."""

from datetime import datetime
from pathlib import Path


def generate_extraction_filename(timestamp: datetime, commit_hash: str) -> str:
    """
    Generate extraction filename.

    Format: extraction_YYYYMMDD_HHMMSS_<commit_hash>.json

    Args:
        timestamp: Timestamp of extraction
        commit_hash: Full or short git commit hash

    Returns:
        Filename string
    """
    # Format timestamp as YYYYMMDD_HHMMSS
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # Use first 7 characters of commit hash
    commit_short = commit_hash[:7]

    return f"extraction_{ts_str}_{commit_short}.json"


def parse_extraction_filename(filename: str) -> tuple[datetime, str] | None:
    """
    Parse extraction filename to extract timestamp and commit hash.

    Args:
        filename: Filename to parse (e.g., "extraction_20250110_143022_abc123.json")

    Returns:
        Tuple of (timestamp, commit_hash) or None if invalid format
    """
    # Remove .json extension if present
    if filename.endswith(".json"):
        filename = filename[:-5]

    # Split by underscore
    parts = filename.split("_")

    # Should have format: extraction_YYYYMMDD_HHMMSS_commithash
    if len(parts) != 4 or parts[0] != "extraction":
        return None

    try:
        # Parse date and time
        date_str = parts[1]  # YYYYMMDD
        time_str = parts[2]  # HHMMSS
        commit_hash = parts[3]

        # Combine and parse
        dt_str = f"{date_str}_{time_str}"
        timestamp = datetime.strptime(dt_str, "%Y%m%d_%H%M%S")

        return (timestamp, commit_hash)
    except (ValueError, IndexError):
        return None


def find_latest_extraction(index_dir: Path) -> Path | None:
    """
    Find most recent extraction file by parsing all filenames.

    Args:
        index_dir: Directory containing extraction files

    Returns:
        Path to latest extraction file, or None if directory empty
    """
    if not index_dir.exists():
        return None

    # Find all extraction files
    extraction_files = list(index_dir.glob("extraction_*.json"))

    if not extraction_files:
        return None

    # Parse timestamps and find latest
    latest_file = None
    latest_timestamp = None

    for file_path in extraction_files:
        parsed = parse_extraction_filename(file_path.name)
        if parsed is None:
            continue

        timestamp, _ = parsed

        if latest_timestamp is None or timestamp > latest_timestamp:
            latest_timestamp = timestamp
            latest_file = file_path

    return latest_file


def list_extractions_chronological(index_dir: Path) -> list[Path]:
    """
    List all extraction files in chronological order.

    Args:
        index_dir: Directory containing extraction files

    Returns:
        List of paths sorted by timestamp (oldest first)
    """
    if not index_dir.exists():
        return []

    # Find all extraction files
    extraction_files = list(index_dir.glob("extraction_*.json"))

    # Parse timestamps and sort
    files_with_timestamps: list[tuple[datetime, Path]] = []

    for file_path in extraction_files:
        parsed = parse_extraction_filename(file_path.name)
        if parsed is None:
            continue

        timestamp, _ = parsed
        files_with_timestamps.append((timestamp, file_path))

    # Sort by timestamp
    files_with_timestamps.sort(key=lambda x: x[0])

    # Return just the paths
    return [path for _, path in files_with_timestamps]
