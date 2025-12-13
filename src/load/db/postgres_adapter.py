"""PostgreSQL database adapter implementation.

This adapter wraps psycopg3 functionality to provide a consistent interface
for database operations across different database backends.
"""

from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
except ImportError as e:
    raise ImportError(
        "PostgreSQL dependencies not installed. "
        'Install with: uv pip install -e ".[postgresql]" or make postgres-install'
    ) from e

from .interface import DatabaseAdapter
from .types import ConnectionError as DBConnectionError
from .types import DatabaseError, Row, SchemaError
from .types import IntegrityError as DBIntegrityError


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter.

    Wraps psycopg3 functionality to implement the DatabaseAdapter interface.
    Uses connection pooling for efficient connection management.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "git_reading",
        user: str = "postgres",
        password: str = "",
        pool_size: int = 5,
        pool_max_overflow: int = 10,
    ):
        """Initialize PostgreSQL adapter.

        Args:
            host: PostgreSQL server host
            port: PostgreSQL server port
            database: Database name
            user: Database user
            password: Database password
            pool_size: Minimum number of connections in pool
            pool_max_overflow: Maximum overflow connections beyond pool_size
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.pool_size = pool_size
        self.pool_max_overflow = pool_max_overflow

        self._pool: ConnectionPool | None = None
        self._conn: Any = None  # psycopg.Connection
        self._schema_file = Path(__file__).parent / "schema_postgresql.sql"

    def connect(self) -> None:
        """Establish database connection and connection pool."""
        try:
            # Build connection string
            conninfo = (
                f"host={self.host} port={self.port} dbname={self.database} "
                f"user={self.user} password={self.password}"
            )

            # Create connection pool
            self._pool = ConnectionPool(
                conninfo,
                min_size=self.pool_size,
                max_size=self.pool_size + self.pool_max_overflow,
            )

            # Get a connection from the pool
            self._conn = self._pool.getconn()

            # Configure connection to return rows as dicts
            self._conn.row_factory = dict_row

        except psycopg.Error as e:
            raise DBConnectionError(f"Failed to connect to PostgreSQL database: {e}") from e

    def close(self) -> None:
        """Close database connection and connection pool."""
        if self._conn and self._pool:
            self._pool.putconn(self._conn)
            self._conn = None

        if self._pool:
            self._pool.close()
            self._pool = None

    def commit(self) -> None:
        """Commit current transaction."""
        if not self._conn:
            raise DatabaseError("No active connection")
        try:
            self._conn.commit()
        except psycopg.Error as e:
            raise DatabaseError(f"Failed to commit transaction: {e}") from e

    def rollback(self) -> None:
        """Rollback current transaction."""
        if not self._conn:
            raise DatabaseError("No active connection")
        try:
            self._conn.rollback()
        except psycopg.Error as e:
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
            with self._conn.cursor() as cursor:
                cursor.execute(schema_sql)
            self._conn.commit()
        except psycopg.Error as e:
            raise SchemaError(f"Failed to create schema: {e}") from e
        except OSError as e:
            raise SchemaError(f"Failed to read schema file: {e}") from e

    def get_tables(self) -> list[str]:
        """Get list of all tables in database."""
        if not self._conn:
            raise DatabaseError("No active connection")

        try:
            query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
            with self._conn.cursor() as cursor:
                cursor.execute(query)
                return [row["table_name"] for row in cursor.fetchall()]
        except psycopg.Error as e:
            raise DatabaseError(f"Failed to get table list: {e}") from e

    def get_table_schema(self, table_name: str) -> list[Row]:
        """Get schema information for a specific table."""
        if not self._conn:
            raise DatabaseError("No active connection")

        try:
            query = """
                SELECT
                    ordinal_position - 1 AS cid,
                    column_name AS name,
                    data_type AS type,
                    CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                    column_default AS "default",
                    CASE WHEN column_name IN (
                        SELECT a.attname
                        FROM pg_index i
                        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                        WHERE i.indrelid = %s::regclass AND i.indisprimary
                    ) THEN 1 ELSE 0 END AS pk
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """
            with self._conn.cursor() as cursor:
                cursor.execute(query, (table_name, table_name))
                return cursor.fetchall()
        except psycopg.Error as e:
            raise DatabaseError(f"Failed to get table schema: {e}") from e

    def execute(self, query: str, params: tuple | None = None) -> Any:
        """Execute a query and return cursor.

        Note: PostgreSQL uses %s placeholders, but this method expects queries
        with ? placeholders (SQLite style) and converts them automatically.
        """
        if not self._conn:
            raise DatabaseError("No active connection")

        try:
            # Convert SQLite-style ? placeholders to PostgreSQL-style %s
            pg_query = query.replace("?", "%s")

            cursor = self._conn.cursor()
            if params:
                cursor.execute(pg_query, params)
            else:
                cursor.execute(pg_query)
            return cursor
        except psycopg.errors.IntegrityError as e:
            raise DBIntegrityError(f"Integrity constraint violation: {e}") from e
        except psycopg.Error as e:
            raise DatabaseError(f"Query execution failed: {e}") from e

    def fetchone(self, query: str, params: tuple | None = None) -> Row | None:
        """Execute query and fetch one result as dictionary."""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        if row is None:
            return None
        # psycopg with dict_row already returns dict
        return dict(row)

    def fetchall(self, query: str, params: tuple | None = None) -> list[Row]:
        """Execute query and fetch all results as list of dictionaries."""
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        # psycopg with dict_row already returns dicts
        return [dict(row) for row in rows]

    def cursor(self) -> Any:
        """Get raw database cursor for complex operations."""
        if not self._conn:
            raise DatabaseError("No active connection")
        return self._conn.cursor()

    @property
    def placeholder(self) -> str:
        """Get database-specific parameter placeholder.

        Returns:
            '%s' for PostgreSQL (but queries with ? are auto-converted)
        """
        return "%s"

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._conn else "disconnected"
        return (
            f"PostgreSQLAdapter(host={self.host}, port={self.port}, "
            f"database={self.database}, status={status})"
        )
