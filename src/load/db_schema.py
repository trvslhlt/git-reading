"""Database schema definition for git-reading metadata storage.

This module provides backward-compatible functions for creating and connecting
to the database, now using the database abstraction layer.
"""

from pathlib import Path

from common.constants import (
    DATABASE_TYPE,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_POOL_MAX_OVERFLOW,
    POSTGRES_POOL_SIZE,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from load.db import DatabaseAdapter, DatabaseConfig
from load.db import create_database as create_db_adapter


def create_database(db_path: str | Path) -> None:
    """Create database with schema for reading notes metadata.

    This function maintains backward compatibility while using the new
    database abstraction layer. It defaults to SQLite but can be configured
    to use PostgreSQL via the DATABASE_TYPE environment variable.

    Args:
        db_path: Path to database file (SQLite) or database name (PostgreSQL)

    Environment Variables:
        DATABASE_TYPE: 'sqlite' (default) or 'postgresql'
        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD:
            PostgreSQL connection settings (only used when DATABASE_TYPE=postgresql)
    """
    db_path = Path(db_path)

    # Choose database backend based on environment variable
    if DATABASE_TYPE.lower() == "postgresql":
        config = DatabaseConfig(
            db_type="postgresql",
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            pool_size=POSTGRES_POOL_SIZE,
            pool_max_overflow=POSTGRES_POOL_MAX_OVERFLOW,
        )
    else:
        # Default to SQLite for backward compatibility
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

    Environment Variables:
        DATABASE_TYPE: 'sqlite' (default) or 'postgresql'
        POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD:
            PostgreSQL connection settings (only used when DATABASE_TYPE=postgresql)
    """
    db_path = Path(db_path)

    # Choose database backend based on environment variable
    if DATABASE_TYPE.lower() == "postgresql":
        config = DatabaseConfig(
            db_type="postgresql",
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            pool_size=POSTGRES_POOL_SIZE,
            pool_max_overflow=POSTGRES_POOL_MAX_OVERFLOW,
        )
    else:
        # Default to SQLite for backward compatibility
        config = DatabaseConfig(db_type="sqlite", db_path=db_path)

    adapter = create_db_adapter(config)
    adapter.connect()
    return adapter
