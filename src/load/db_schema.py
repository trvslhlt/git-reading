"""Database schema definition for git-reading metadata storage.

This module provides backward-compatible functions for creating and connecting
to the database, now using the database abstraction layer.
"""

from pathlib import Path

from load.db import DatabaseAdapter, DatabaseConfig
from load.db import create_database as create_db_adapter


def create_database(db_path: str | Path) -> None:
    """Create database with schema for reading notes metadata.

    This function maintains backward compatibility while using the new
    database abstraction layer. It defaults to SQLite but can be configured
    to use other databases via environment variables.

    Args:
        db_path: Path to database file (SQLite) or database name (PostgreSQL)
    """
    db_path = Path(db_path)

    # For now, always use SQLite to maintain backward compatibility
    # Future: could read DATABASE_TYPE from environment to choose backend
    config = DatabaseConfig(db_type="sqlite", db_path=db_path)

    adapter = create_db_adapter(config)
    adapter.connect()
    adapter.create_schema()
    adapter.close()


def get_connection(db_path: str | Path) -> DatabaseAdapter:
    """Get a connection to the database.

    This function maintains backward compatibility while returning the new
    DatabaseAdapter interface. The adapter provides a consistent API across
    different database backends.

    Args:
        db_path: Path to database file (SQLite) or database name (PostgreSQL)

    Returns:
        Database adapter with connection established
    """
    db_path = Path(db_path)

    # For now, always use SQLite to maintain backward compatibility
    config = DatabaseConfig(db_type="sqlite", db_path=db_path)

    adapter = create_db_adapter(config)
    adapter.connect()
    return adapter
