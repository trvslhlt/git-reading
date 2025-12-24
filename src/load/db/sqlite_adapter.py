"""SQLite database adapter implementation.

This adapter wraps SQLite3 functionality to provide a consistent interface
for database operations across different database backends.
"""

import sqlite3
from pathlib import Path
from typing import Any

from .interface import DatabaseAdapter
from .types import ConnectionError as DBConnectionError
from .types import DatabaseError, Row, SchemaError
from .types import IntegrityError as DBIntegrityError


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter.

    Wraps sqlite3 functionality to implement the DatabaseAdapter interface.
    """

    def __init__(self, db_path: str | Path):
        """Initialize SQLite adapter.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._schema_file = Path(__file__).parent / "schema_sqlite.sql"

    def connect(self) -> None:
        """Establish database connection."""
        try:
            # Create parent directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        except sqlite3.Error as e:
            raise DBConnectionError(f"Failed to connect to SQLite database: {e}") from e

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        """Commit current transaction."""
        if not self._conn:
            raise DatabaseError("No active connection")
        try:
            self._conn.commit()
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to commit transaction: {e}") from e

    def rollback(self) -> None:
        """Rollback current transaction."""
        if not self._conn:
            raise DatabaseError("No active connection")
        try:
            self._conn.rollback()
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to rollback transaction: {e}") from e

    def create_schema(self) -> None:
        """Create all database tables and indexes from SQL file."""
        if not self._conn:
            raise DatabaseError("No active connection")

        if not self._schema_file.exists():
            raise SchemaError(f"Schema file not found: {self._schema_file}")

        try:
            with open(self._schema_file) as f:
                schema_sql = f.read()

            # Execute all statements in the schema file
            self._conn.executescript(schema_sql)
            self._conn.commit()
        except sqlite3.Error as e:
            raise SchemaError(f"Failed to create schema: {e}") from e
        except OSError as e:
            raise SchemaError(f"Failed to read schema file: {e}") from e

    def get_tables(self) -> list[str]:
        """Get list of all tables in database."""
        if not self._conn:
            raise DatabaseError("No active connection")

        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get table list: {e}") from e

    def get_table_schema(self, table_name: str) -> list[Row]:
        """Get schema information for a specific table."""
        if not self._conn:
            raise DatabaseError("No active connection")

        try:
            cursor = self._conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            rows = cursor.fetchall()

            # Convert to standard format
            schema = []
            for row in rows:
                schema.append(
                    {
                        "cid": row[0],
                        "name": row[1],
                        "type": row[2],
                        "notnull": row[3],
                        "default": row[4],
                        "pk": row[5],
                    }
                )
            return schema
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to get table schema: {e}") from e

    def execute(self, query: str, params: tuple | None = None) -> Any:
        """Execute a query and return cursor."""
        if not self._conn:
            raise DatabaseError("No active connection")

        try:
            cursor = self._conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
        except sqlite3.IntegrityError as e:
            raise DBIntegrityError(f"Integrity constraint violation: {e}") from e
        except sqlite3.Error as e:
            raise DatabaseError(f"Query execution failed: {e}") from e

    def fetchone(self, query: str, params: tuple | None = None) -> Row | None:
        """Execute query and fetch one result as dictionary."""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        # Convert sqlite3.Row to dict
        return dict(row)

    def fetchall(self, query: str, params: tuple | None = None) -> list[Row]:
        """Execute query and fetch all results as list of dictionaries."""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        # Convert sqlite3.Row objects to dicts
        return [dict(row) for row in rows]

    def fetchscalar(self, query: str, params: tuple | None = None) -> Any:
        """Execute query and return first column of first row."""
        result = self.fetchone(query, params)
        if result is None:
            return None
        # Get first value from the dictionary
        return result[list(result.keys())[0]]

    def cursor(self) -> Any:
        """Get raw database cursor for complex operations."""
        if not self._conn:
            raise DatabaseError("No active connection")
        return self._conn.cursor()

    @property
    def placeholder(self) -> str:
        """Get database-specific parameter placeholder.

        Returns:
            '?' for SQLite
        """
        return "?"

    def exists(self) -> bool:
        """Check if SQLite database file exists."""
        return self.db_path.exists()

    def delete(self) -> None:
        """Delete SQLite database file."""
        if self._conn:
            self.close()
        if self.db_path.exists():
            self.db_path.unlink()

    def drop_schema(self) -> None:
        """Drop all tables in SQLite database."""
        if not self._conn:
            raise DatabaseError("No active connection")

        cursor = self._conn.cursor()
        tables = self.get_tables()
        # Filter out sqlite_sequence (automatically maintained by SQLite)
        tables = [t for t in tables if t != "sqlite_sequence"]
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        self._conn.commit()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._conn else "disconnected"
        return f"SQLiteAdapter(db_path={self.db_path}, status={status})"
