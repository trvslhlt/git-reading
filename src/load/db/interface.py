"""Abstract database adapter interface.

This module defines the interface that all database adapters must implement,
providing a consistent API for database operations across SQLite and PostgreSQL.
"""

from abc import ABC, abstractmethod
from typing import Any

from .types import Row


class DatabaseAdapter(ABC):
    """Abstract database adapter interface.

    All database implementations (SQLite, PostgreSQL) must implement this interface
    to ensure consistent behavior across different database backends.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit current transaction.

        Raises:
            DatabaseError: If commit fails
        """
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback current transaction.

        Raises:
            DatabaseError: If rollback fails
        """
        pass

    @abstractmethod
    def create_schema(self) -> None:
        """Create all database tables and indexes.

        This method creates the base schema. After calling this, run_migrations()
        should be called to apply any pending schema updates.

        Raises:
            SchemaError: If schema creation fails
        """
        pass

    def run_migrations(self) -> int:
        """Run pending database migrations.

        Returns:
            Number of migrations applied

        Raises:
            DatabaseError: If migration fails
        """
        from .migrations import MigrationRunner

        runner = MigrationRunner(self)
        return runner.run_migrations()

    @abstractmethod
    def get_tables(self) -> list[str]:
        """Get list of all tables in database.

        Returns:
            List of table names

        Raises:
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> list[Row]:
        """Get schema information for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            List of column definitions as dictionaries with keys:
                - name: Column name
                - type: Column data type
                - notnull: Whether column is NOT NULL (1 or 0)
                - default: Default value (or None)
                - pk: Whether column is primary key (1 or 0)

        Raises:
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    def execute(self, query: str, params: tuple | None = None) -> Any:
        """Execute a query and return cursor.

        Args:
            query: SQL query to execute
            params: Query parameters (optional)

        Returns:
            Database cursor

        Raises:
            DatabaseError: If execution fails
            IntegrityError: If integrity constraint violated
        """
        pass

    @abstractmethod
    def fetchone(self, query: str, params: tuple | None = None) -> Row | None:
        """Execute query and fetch one result as dictionary.

        Args:
            query: SQL query to execute
            params: Query parameters (optional)

        Returns:
            Single row as dictionary, or None if no results

        Raises:
            DatabaseError: If execution fails
        """
        pass

    @abstractmethod
    def fetchall(self, query: str, params: tuple | None = None) -> list[Row]:
        """Execute query and fetch all results as list of dictionaries.

        Args:
            query: SQL query to execute
            params: Query parameters (optional)

        Returns:
            List of rows as dictionaries

        Raises:
            DatabaseError: If execution fails
        """
        pass

    @abstractmethod
    def fetchscalar(self, query: str, params: tuple | None = None) -> Any:
        """Execute query and return first column of first row.

        Useful for queries that return a single value like COUNT(*), MAX(), etc.

        Args:
            query: SQL query to execute
            params: Query parameters (optional)

        Returns:
            First column of first row, or None if no results

        Raises:
            DatabaseError: If execution fails
        """
        pass

    @abstractmethod
    def cursor(self) -> Any:
        """Get raw database cursor for complex operations.

        Returns:
            Database cursor object

        Raises:
            DatabaseError: If cursor creation fails
        """
        pass

    @property
    @abstractmethod
    def placeholder(self) -> str:
        """Get database-specific parameter placeholder.

        Returns:
            Parameter placeholder string ('?' for SQLite, '%s' for PostgreSQL)
        """
        pass

    @abstractmethod
    def exists(self) -> bool:
        """Check if database exists and is accessible.

        For SQLite: Checks if database file exists
        For PostgreSQL: Checks if database exists and has tables

        Returns:
            True if database exists and is accessible, False otherwise
        """
        pass

    @abstractmethod
    def delete(self) -> None:
        """Delete/drop the database.

        For SQLite: Deletes the database file
        For PostgreSQL: Drops all tables (CASCADE)

        Raises:
            DatabaseError: If deletion fails
        """
        pass

    @abstractmethod
    def drop_schema(self) -> None:
        """Drop all tables in the database.

        Similar to delete() but doesn't remove the database itself.
        Already implemented in PostgreSQLAdapter, needs SQLite implementation.

        Raises:
            SchemaError: If schema drop fails
        """
        pass

    @abstractmethod
    def string_agg(self, column: str, separator: str = ",", distinct: bool = False) -> str:
        """Generate database-specific string aggregation SQL.

        Args:
            column: Column name to aggregate
            separator: Separator for concatenated strings (default: ',')
            distinct: Whether to use DISTINCT (default: False)

        Returns:
            SQL string for aggregating strings
            - PostgreSQL: string_agg(column, separator)
            - SQLite: GROUP_CONCAT(column)

        Example:
            >>> adapter.string_agg('bs.source', ',', distinct=True)
            'string_agg(DISTINCT bs.source, ',')'  # PostgreSQL
            'GROUP_CONCAT(DISTINCT bs.source)'     # SQLite
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()
        return False
