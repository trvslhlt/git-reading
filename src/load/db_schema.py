"""Database schema definition for git-reading metadata storage.

This module provides backward-compatible functions for creating and connecting
to the database, now using the database abstraction layer.
"""

from load.db import DatabaseAdapter, get_adapter


def create_database() -> None:
    """Create database with schema for reading notes metadata.

    Database configuration is read from environment variables.
    """
    adapter = get_adapter()
    adapter.connect()
    adapter.create_schema()
    adapter.close()


def get_connection() -> DatabaseAdapter:
    """Get a connection to the database.

    Database configuration is read from environment variables.

    Returns:
        Database adapter with connection established
    """
    adapter = get_adapter()
    adapter.connect()
    return adapter
