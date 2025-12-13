"""Database abstraction layer for git-reading.

This package provides a consistent interface for database operations across
SQLite and PostgreSQL backends.

Example:
    >>> from load.db import DatabaseConfig, create_database
    >>>
    >>> # Create SQLite adapter
    >>> config = DatabaseConfig(db_type="sqlite", db_path="data/readings.db")
    >>> adapter = create_database(config)
    >>>
    >>> # Use the adapter
    >>> adapter.connect()
    >>> adapter.create_schema()
    >>> adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("test", "value"))
    >>> adapter.commit()
    >>> adapter.close()
"""

from .factory import DatabaseConfig, create_database
from .interface import DatabaseAdapter
from .sqlite_adapter import SQLiteAdapter
from .types import (
    ConnectionError,
    DatabaseError,
    DatabaseType,
    IntegrityError,
    Row,
    SchemaError,
)

__all__ = [
    # Factory
    "DatabaseConfig",
    "create_database",
    # Interface
    "DatabaseAdapter",
    # Adapters
    "SQLiteAdapter",
    # Types and exceptions
    "DatabaseType",
    "DatabaseError",
    "ConnectionError",
    "IntegrityError",
    "SchemaError",
    "Row",
]
