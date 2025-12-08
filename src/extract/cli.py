#!/usr/bin/env python3
"""CLI interface for extract module."""

import argparse
from pathlib import Path

from .main import index_notes


def cmd_readings(args):
    """Extract and index reading notes.

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

    index_notes(args.notes_dir, args.output, args.git_dir)
    return 0


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
        "--output",
        type=Path,
        default=Path("book_index.json"),
        help="Output JSON file path (default: book_index.json)",
    )
    readings_parser.set_defaults(func=cmd_readings)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    exit(main())
