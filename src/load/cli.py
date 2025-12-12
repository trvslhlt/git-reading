"""CLI for database operations."""

import argparse
import sys
from pathlib import Path

from load.migrate_to_db import (
    migrate_from_extractions,
    migrate_incremental,
)


def cmd_migrate(args):
    """Migrate from extraction files to SQLite database."""
    db_path = Path(args.database)
    index_dir = Path(args.index_dir)

    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        print("Run 'make run-extract' first to create extraction files.")
        sys.exit(1)

    if args.incremental:
        # Incremental update mode
        if not db_path.exists():
            print(f"Error: Database not found: {db_path}")
            print("Run full migration first (without --incremental).")
            sys.exit(1)

        migrate_incremental(index_dir, db_path, verbose=True)

    else:
        # Full rebuild mode
        if db_path.exists() and not args.force:
            print(f"Error: Database already exists: {db_path}")
            print("Use --force to overwrite or --incremental to update.")
            sys.exit(1)

        if args.force and db_path.exists():
            db_path.unlink()
            print(f"Removed existing database: {db_path}")

        migrate_from_extractions(index_dir, db_path, verbose=True)


def main():
    """Main entry point for the load CLI."""
    parser = argparse.ArgumentParser(
        description="Database operations for reading notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Migrate command
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Migrate from extraction files to SQLite database",
    )

    migrate_parser.add_argument(
        "--index-dir",
        "-i",
        required=True,
        help="Path to directory containing extraction files",
    )
    migrate_parser.add_argument(
        "--database",
        "-d",
        required=True,
        help="Path to SQLite database file",
    )
    migrate_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Apply incremental updates (requires existing database)",
    )
    migrate_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "migrate":
        cmd_migrate(args)


if __name__ == "__main__":
    main()
