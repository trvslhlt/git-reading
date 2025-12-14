"""CLI for database operations."""

import argparse
import sys
from pathlib import Path

from load.db import get_adapter
from load.load_data import (
    load_from_extractions,
    load_incremental,
)


def cmd_load(args):
    """Load data from extraction files to database.

    Database configuration is read from environment variables (see .env file).
    Configure DATABASE_TYPE, DATABASE_PATH (SQLite), or POSTGRES_* settings.
    """
    index_dir = Path(args.index_dir)

    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        print("Run 'extract readings' first to create extraction files.")
        sys.exit(1)

    # Create adapter using .env configuration
    adapter = get_adapter()

    if args.incremental:
        # Incremental update mode
        if not adapter.exists():
            print("Error: Database not found or has no tables")
            print("Run full load first (without --incremental).")
            sys.exit(1)
        load_incremental(index_dir, verbose=True)
    else:
        # Full rebuild mode
        if adapter.exists() and not args.force:
            print("Error: Database already exists")
            print("Use --force to overwrite or --incremental to update.")
            sys.exit(1)

        if args.force and adapter.exists():
            adapter.delete()
            print("Removed existing database")

        load_from_extractions(index_dir, verbose=True, force=False)


def main():
    """Main entry point for the load CLI."""
    parser = argparse.ArgumentParser(
        description="Database operations for reading notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Load command
    load_parser = subparsers.add_parser(
        "load",
        help="Load data from extraction files to database",
        description=(
            "Load reading notes from extraction files to database.\n\n"
            "Database configuration is read from .env file:\n"
            "  - DATABASE_TYPE: 'sqlite' or 'postgresql'\n"
            "  - DATABASE_PATH: Path to SQLite database file (if using SQLite)\n"
            "  - POSTGRES_*: PostgreSQL connection settings (if using PostgreSQL)\n\n"
            "Examples:\n"
            "  # Load data using .env configuration\n"
            "  load-db load --index-dir data/index\n\n"
            "  # Incremental update\n"
            "  load-db load --index-dir data/index --incremental\n\n"
            "  # Force rebuild (drops all tables)\n"
            "  load-db load --index-dir data/index --force\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    load_parser.add_argument(
        "--index-dir",
        "-i",
        required=True,
        help="Path to directory containing extraction files",
    )
    load_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Apply incremental updates (requires existing database)",
    )
    load_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database (drops and recreates all tables)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "load":
        cmd_load(args)


if __name__ == "__main__":
    main()
