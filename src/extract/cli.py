#!/usr/bin/env python3
"""CLI interface for extract module."""

import argparse
from pathlib import Path

from .main import extract_full, extract_incremental


def cmd_readings(args):
    """Extract and index reading notes using incremental extraction.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    if not args.notes_dir.is_dir():
        print(f"Error: {args.notes_dir} is not a directory")
        return 1

    if args.git_dir and not args.git_dir.is_dir():
        print(f"Error: {args.git_dir} is not a directory")
        return 1

    try:
        if args.full:
            # Force full re-extraction
            extract_full(args.notes_dir, args.index_dir, args.git_dir)
        else:
            # Incremental extraction (default)
            result = extract_incremental(args.notes_dir, args.index_dir, args.git_dir)
            if result is None:
                # No changes detected, but still return success
                pass

        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Extract and index data from various sources")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Readings command
    readings_parser = subparsers.add_parser(
        "readings", help="Extract and index reading notes from markdown files"
    )
    readings_parser.add_argument(
        "--notes-dir",
        type=Path,
        required=True,
        help="Directory containing markdown notes",
    )
    readings_parser.add_argument(
        "--git-dir",
        type=Path,
        default=None,
        help="Git repository directory (default: auto-detect from notes-dir)",
    )
    readings_parser.add_argument(
        "--index-dir",
        type=Path,
        default=Path("./index"),
        help="Directory to write extraction files (default: ./index)",
    )
    readings_parser.add_argument(
        "--full",
        action="store_true",
        help="Force full re-extraction (default: incremental)",
    )
    readings_parser.set_defaults(func=cmd_readings)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    exit(main())
