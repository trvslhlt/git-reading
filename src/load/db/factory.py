"""Database factory for creating database adapters.

This module provides a factory function and configuration class for creating
database adapters based on the database type (SQLite or PostgreSQL).
"""

from dataclasses import dataclass
from pathlib import Path

from .interface import DatabaseAdapter
from .sqlite_adapter import SQLiteAdapter
from .types import DatabaseType


@dataclass
class DatabaseConfig:
    """Database configuration container.

    Attributes:
        db_type: Type of database ('sqlite' or 'postgresql')
        db_path: Path to SQLite database file (for SQLite only)
        host: PostgreSQL host (for PostgreSQL only)
        port: PostgreSQL port (for PostgreSQL only)
        database: PostgreSQL database name (for PostgreSQL only)
        user: PostgreSQL username (for PostgreSQL only)
        password: PostgreSQL password (for PostgreSQL only)
    """

    db_type: DatabaseType | str
    # SQLite-specific
    db_path: Path | None = None
    # PostgreSQL-specific
    host: str | None = None
    port: int | None = None
    database: str | None = None
    user: str | None = None
    password: str | None = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Convert string to DatabaseType enum
        if isinstance(self.db_type, str):
            try:
                self.db_type = DatabaseType(self.db_type.lower())
            except ValueError as e:
                raise ValueError(
                    f"Unsupported database type: {self.db_type}. "
                    f"Must be one of: {', '.join(t.value for t in DatabaseType)}"
                ) from e

        # Validate type-specific configuration
        if self.db_type == DatabaseType.SQLITE:
            if self.db_path is None:
                raise ValueError("db_path is required for SQLite")
            # Convert to Path if string
            if isinstance(self.db_path, str):
                self.db_path = Path(self.db_path)

        elif self.db_type == DatabaseType.POSTGRESQL:
            if not all([self.host, self.database, self.user]):
                raise ValueError("host, database, and user are required for PostgreSQL")
            # Set default port if not provided
            if self.port is None:
                self.port = 5432


def create_database(config: DatabaseConfig) -> DatabaseAdapter:
    """Factory function to create appropriate database adapter.

    Args:
        config: Database configuration

    Returns:
        Database adapter instance

    Raises:
        ValueError: If database type is unsupported or configuration is invalid

    Example:
        >>> # SQLite
        >>> config = DatabaseConfig(
        ...     db_type="sqlite",
        ...     db_path=Path("./data/readings.db")
        ... )
        >>> adapter = create_database(config)
        >>>
        >>> # PostgreSQL
        >>> config = DatabaseConfig(
        ...     db_type="postgresql",
        ...     host="localhost",
        ...     port=5432,
        ...     database="git_reading",
        ...     user="postgres",
        ...     password="password"
        ... )
        >>> adapter = create_database(config)
    """
    if config.db_type == DatabaseType.SQLITE:
        return SQLiteAdapter(config.db_path)

    elif config.db_type == DatabaseType.POSTGRESQL:
        # Import here to avoid requiring psycopg when not using PostgreSQL
        try:
            from .postgres_adapter import PostgreSQLAdapter
        except ImportError as e:
            raise ImportError(
                "PostgreSQL support requires psycopg. Install with: pip install '.[postgresql]'"
            ) from e

        return PostgreSQLAdapter(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password,
        )

    else:
        # This should never happen due to enum validation
        raise ValueError(f"Unsupported database type: {config.db_type}")
