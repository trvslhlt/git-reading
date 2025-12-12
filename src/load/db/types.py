"""Shared types and exceptions for database abstraction layer."""

from enum import Enum
from typing import Any


class DatabaseType(str, Enum):
    """Supported database types."""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class ConnectionError(DatabaseError):
    """Error connecting to database."""

    pass


class IntegrityError(DatabaseError):
    """Database integrity constraint violation."""

    pass


class SchemaError(DatabaseError):
    """Error with database schema."""

    pass


# Type alias for database rows
Row = dict[str, Any]
