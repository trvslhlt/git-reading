"""Database schema definition for git-reading metadata storage.

This module provides backward-compatible functions for creating and connecting
to the database, now using the database abstraction layer.
"""

from pathlib import Path

from common.env import env
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
    db_type = env.database_type()
    if db_type.lower() == "postgresql":
        config = DatabaseConfig(
            db_type="postgresql",
            host=env.postgres_host(),
            port=env.postgres_port(),
            database=env.postgres_database(),
            user=env.postgres_user(),
            password=env.postgres_password(),
            pool_size=env.postgres_pool_size(),
            pool_max_overflow=env.postgres_pool_max_overflow(),
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
    # Read directly from environment to allow test fixtures to override
    db_type = env.database_type()
    if db_type.lower() == "postgresql":
        config = DatabaseConfig(
            db_type="postgresql",
            host=env.postgres_host(),
            port=env.postgres_port(),
            database=env.postgres_database(),
            user=env.postgres_user(),
            password=env.postgres_password(),
            pool_size=env.postgres_pool_size(),
            pool_max_overflow=env.postgres_pool_max_overflow(),
        )
    else:
        # Default to SQLite for backward compatibility
        config = DatabaseConfig(db_type="sqlite", db_path=db_path)

    adapter = create_db_adapter(config)
    adapter.connect()
    return adapter
