"""CLI for database operations."""

import argparse
import sys
from pathlib import Path

from common.env import env
from load.load_data import (
    load_from_extractions,
    load_incremental,
)


def cmd_load(args):
    """Load data from extraction files to database.

    The database argument is interpreted based on DATABASE_TYPE:
    - SQLite: File path (e.g., 'data/readings.db')
    - PostgreSQL: Database name (e.g., 'readings')
    """
    database = args.database
    index_dir = Path(args.index_dir)
    db_type = env.database_type()

    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        print("Run 'extract readings' first to create extraction files.")
        sys.exit(1)

    # For SQLite, convert to Path and check file existence
    if db_type.lower() == "sqlite":
        db_path = Path(database)

        if args.incremental:
            # Incremental update mode
            if not db_path.exists():
                print(f"Error: Database not found: {db_path}")
                print("Run full load first (without --incremental).")
                sys.exit(1)

            load_incremental(index_dir, db_path, verbose=True)

        else:
            # Full rebuild mode
            if db_path.exists() and not args.force:
                print(f"Error: Database already exists: {db_path}")
                print("Use --force to overwrite or --incremental to update.")
                sys.exit(1)

            if args.force and db_path.exists():
                db_path.unlink()
                print(f"Removed existing database: {db_path}")

            load_from_extractions(index_dir, db_path, verbose=True, force=False)

    else:
        # PostgreSQL - database is a name, not a file path
        if args.incremental:
            load_incremental(index_dir, database, verbose=True)
        else:
            # Check if tables already exist (unless force is specified)
            if not args.force:
                from load.db_schema import get_connection
                adapter = get_connection(database)
                tables = adapter.get_tables()
                adapter.close()

                if tables:
                    print(f"Error: Database '{database}' already has tables: {', '.join(tables)}")
                    print("Use --force to drop and recreate tables or --incremental to update.")
                    sys.exit(1)
            else:
                print("Warning: --force flag drops and recreates all tables in PostgreSQL")

            load_from_extractions(index_dir, database, verbose=True, force=args.force)


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
            "Database backend is controlled by DATABASE_TYPE environment variable:\n"
            "  - SQLite (DATABASE_TYPE=sqlite): Provide file path (e.g., 'data/readings.db')\n"
            "  - PostgreSQL (DATABASE_TYPE=postgresql): Provide database name (e.g., 'readings')\n"
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
        "--database",
        "-d",
        required=True,
        help="Database file path (SQLite) or database name (PostgreSQL)",
    )
    load_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Apply incremental updates (requires existing database)",
    )
    load_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database (SQLite) or drop/recreate tables (PostgreSQL)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "load":
        cmd_load(args)


if __name__ == "__main__":
    main()
