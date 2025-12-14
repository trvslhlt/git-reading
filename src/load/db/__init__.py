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

from .factory import DatabaseConfig, create_database, get_adapter
from .interface import DatabaseAdapter
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
    "get_adapter",
    # Interface
    "DatabaseAdapter",
    # Types and exceptions
    "DatabaseType",
    "DatabaseError",
    "ConnectionError",
    "IntegrityError",
    "SchemaError",
    "Row",
]
