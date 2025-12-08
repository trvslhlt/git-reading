"""CLI for database operations."""

import argparse
import sys
from pathlib import Path

from load.migrate_to_db import migrate_from_json, verify_migration


def cmd_migrate(args):
    """Migrate from JSON to SQLite database."""
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index file not found: {index_path}")
        print("Run 'make run-extract' first to create the index.")
        sys.exit(1)

    db_path = Path(args.database)

    if db_path.exists() and not args.force:
        print(f"Error: Database already exists: {db_path}")
        print("Use --force to overwrite.")
        sys.exit(1)

    if args.force and db_path.exists():
        db_path.unlink()
        print(f"Removed existing database: {db_path}")

    migrate_from_json(index_path, db_path, verbose=True)

    if args.verify:
        verify_migration(db_path, index_path)


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
        help="Migrate from JSON index to SQLite database",
    )
    migrate_parser.add_argument(
        "--index",
        "-i",
        required=True,
        help="Path to JSON index file",
    )
    migrate_parser.add_argument(
        "--database",
        "-d",
        required=True,
        help="Path to SQLite database file",
    )
    migrate_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database",
    )
    migrate_parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Verify migration after completion (default: True)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "migrate":
        cmd_migrate(args)


if __name__ == "__main__":
    main()
