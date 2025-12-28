"""Tests for database adapters."""

import os
from pathlib import Path

import pytest

from load.db import DatabaseConfig, IntegrityError, create_database
from load.db.postgres_adapter import PostgreSQLAdapter
from load.db.sqlite_adapter import SQLiteAdapter

# Skip PostgreSQL integration tests unless explicitly enabled
# (These tests require a running PostgreSQL instance)
POSTGRES_INTEGRATION_ENABLED = os.getenv("RUN_POSTGRES_TESTS") == "1"


class TestSQLiteAdapter:
    """Tests for SQLite adapter."""

    def test_create_adapter(self, tmp_path):
        """Test creating a SQLite adapter."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        assert adapter.db_path == db_path
        assert adapter._conn is None

    def test_connect_and_close(self, tmp_path):
        """Test connecting to and closing database."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)

        adapter.connect()
        assert adapter._conn is not None

        adapter.close()
        assert adapter._conn is None

    def test_create_schema(self, tmp_path):
        """Test creating database schema."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()

        adapter.create_schema()

        # Verify tables were created
        tables = adapter.get_tables()
        expected_tables = [
            "author_influences",
            "author_movements",
            "authors",
            "book_authors",
            "book_subjects",
            "books",
            "enrichment_log",
            "literary_movements",
            "manual_tags",
            "metadata",
            "notes",
            "subjects",
        ]
        # Filter out sqlite_sequence (created automatically for AUTOINCREMENT)
        tables = [t for t in tables if t != "sqlite_sequence"]
        assert sorted(tables) == expected_tables

        adapter.close()

    def test_get_table_schema(self, tmp_path):
        """Test getting table schema information."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()
        adapter.create_schema()

        schema = adapter.get_table_schema("books")
        assert len(schema) > 0

        # Check for expected columns
        column_names = [col["name"] for col in schema]
        assert "id" in column_names
        assert "title" in column_names

        adapter.close()

    def test_execute_and_fetchone(self, tmp_path):
        """Test executing query and fetching one result."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()
        adapter.create_schema()

        # Insert test data
        adapter.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            ("test_key", "test_value"),
        )
        adapter.commit()

        # Fetch the data
        result = adapter.fetchone("SELECT key, value FROM metadata WHERE key = ?", ("test_key",))
        assert result is not None
        assert result["key"] == "test_key"
        assert result["value"] == "test_value"

        adapter.close()

    def test_execute_and_fetchall(self, tmp_path):
        """Test executing query and fetching all results."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()
        adapter.create_schema()

        # Insert multiple rows
        adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("key1", "value1"))
        adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("key2", "value2"))
        adapter.commit()

        # Fetch all
        results = adapter.fetchall("SELECT key, value FROM metadata ORDER BY key")
        assert len(results) == 2
        assert results[0]["key"] == "key1"
        assert results[1]["key"] == "key2"

        adapter.close()

    def test_commit_and_rollback(self, tmp_path):
        """Test transaction commit and rollback."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()
        adapter.create_schema()

        # Test commit
        adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("commit_test", "value"))
        adapter.commit()

        result = adapter.fetchone("SELECT value FROM metadata WHERE key = ?", ("commit_test",))
        assert result is not None

        # Test rollback
        adapter.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            ("rollback_test", "value"),
        )
        adapter.rollback()

        result = adapter.fetchone("SELECT value FROM metadata WHERE key = ?", ("rollback_test",))
        assert result is None

        adapter.close()

    def test_integrity_error(self, tmp_path):
        """Test that integrity errors are properly raised."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()
        adapter.create_schema()

        # Insert a row with primary key
        adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("pk_test", "value1"))
        adapter.commit()

        # Try to insert duplicate primary key
        with pytest.raises(IntegrityError):
            adapter.execute(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                ("pk_test", "value2"),
            )

        adapter.close()

    def test_context_manager(self, tmp_path):
        """Test using adapter as context manager."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)

        with adapter:
            adapter.create_schema()
            adapter.execute(
                "INSERT INTO metadata (key, value) VALUES (?, ?)", ("ctx_test", "value")
            )

        # Verify data was committed
        adapter.connect()
        result = adapter.fetchone("SELECT value FROM metadata WHERE key = ?", ("ctx_test",))
        assert result is not None
        assert result["value"] == "value"
        adapter.close()

    def test_placeholder_property(self, tmp_path):
        """Test placeholder property."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        assert adapter.placeholder == "?"

    def test_cursor_method(self, tmp_path):
        """Test getting raw cursor."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()

        cursor = adapter.cursor()
        assert cursor is not None

        adapter.close()

    def test_exists_method(self, tmp_path):
        """Test exists() method."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)

        # Database file doesn't exist yet
        assert not adapter.exists()

        # Create the database
        adapter.connect()
        adapter.create_schema()
        adapter.close()

        # Now it should exist
        assert adapter.exists()

    def test_delete_method(self, tmp_path):
        """Test delete() method."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()
        adapter.create_schema()
        adapter.close()

        # Database exists
        assert adapter.exists()

        # Delete it
        adapter.delete()

        # Should no longer exist
        assert not adapter.exists()

    def test_drop_schema_method(self, tmp_path):
        """Test drop_schema() method."""
        db_path = tmp_path / "test.db"
        adapter = SQLiteAdapter(db_path)
        adapter.connect()
        adapter.create_schema()

        # Verify tables exist
        tables = adapter.get_tables()
        tables = [t for t in tables if t != "sqlite_sequence"]
        assert len(tables) > 0

        # Drop all tables
        adapter.drop_schema()

        # Verify tables are gone
        tables = adapter.get_tables()
        tables = [t for t in tables if t != "sqlite_sequence"]
        assert len(tables) == 0

        adapter.close()


class TestDatabaseFactory:
    """Tests for database factory."""

    def test_create_sqlite_from_config(self, tmp_path):
        """Test creating SQLite adapter from config."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_type="sqlite", db_path=db_path)

        adapter = create_database(config)
        assert isinstance(adapter, SQLiteAdapter)
        assert adapter.db_path == db_path

    def test_config_validates_sqlite_requirements(self):
        """Test that config validates SQLite requirements."""
        with pytest.raises(ValueError, match="db_path is required"):
            DatabaseConfig(db_type="sqlite")

    def test_config_converts_string_to_enum(self, tmp_path):
        """Test that config converts string to DatabaseType enum."""
        db_path = tmp_path / "test.db"
        config = DatabaseConfig(db_type="sqlite", db_path=db_path)

        from load.db import DatabaseType

        assert config.db_type == DatabaseType.SQLITE

    def test_config_rejects_invalid_type(self):
        """Test that config rejects invalid database type."""
        with pytest.raises(ValueError, match="Unsupported database type"):
            DatabaseConfig(db_type="invalid", db_path="test.db")

    def test_config_converts_string_path_to_path_object(self):
        """Test that config converts string paths to Path objects."""
        config = DatabaseConfig(db_type="sqlite", db_path="test.db")
        assert isinstance(config.db_path, Path)

    def test_get_adapter_sqlite(self, monkeypatch, tmp_path):
        """Test get_adapter() creates SQLite adapter from env."""
        from load.db import get_adapter

        monkeypatch.setenv("DATABASE_TYPE", "sqlite")
        monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))

        adapter = get_adapter()
        assert isinstance(adapter, SQLiteAdapter)

    def test_get_adapter_postgresql(self, monkeypatch):
        """Test get_adapter() creates PostgreSQL adapter from env."""
        pytest.importorskip("psycopg")

        from load.db import get_adapter

        monkeypatch.setenv("DATABASE_TYPE", "postgresql")
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_DB", "test_db")
        monkeypatch.setenv("POSTGRES_USER", "test_user")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test_pass")

        adapter = get_adapter()
        assert isinstance(adapter, PostgreSQLAdapter)


@pytest.mark.skipif(
    not POSTGRES_INTEGRATION_ENABLED, reason="PostgreSQL integration tests not enabled"
)
class TestPostgreSQLAdapter:
    """Tests for PostgreSQL adapter.

    These integration tests require a running PostgreSQL instance and are skipped by default.

    To run these tests:
    1. Start PostgreSQL: make postgres-up
    2. Set environment: export RUN_POSTGRES_TESTS=1
    3. Run tests: make test

    Note: psycopg is always installed as a test dependency, so unit tests for the
    PostgreSQL adapter (like factory tests) run by default without needing a database.
    """

    @pytest.fixture
    def pg_config(self):
        """Get PostgreSQL configuration from environment."""
        return {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "database": os.getenv("POSTGRES_DB", "git_reading"),
            "user": os.getenv("POSTGRES_USER", "git_reading_user"),
            "password": os.getenv("POSTGRES_PASSWORD", "dev_password"),
        }

    @pytest.fixture
    def pg_adapter(self, pg_config):
        """Create and setup a PostgreSQL adapter for testing."""
        adapter = PostgreSQLAdapter(**pg_config)
        adapter.connect()

        # Create schema
        adapter.create_schema()

        yield adapter

        # Cleanup - drop all tables
        tables = adapter.get_tables()
        for table in tables:
            adapter.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        adapter.commit()
        adapter.close()

    def test_create_adapter(self, pg_config):
        """Test creating a PostgreSQL adapter."""
        adapter = PostgreSQLAdapter(**pg_config)
        assert adapter.host == pg_config["host"]
        assert adapter.port == pg_config["port"]
        assert adapter.database == pg_config["database"]
        assert adapter._conn is None

    def test_connect_and_close(self, pg_config):
        """Test connecting to and closing database."""
        adapter = PostgreSQLAdapter(**pg_config)

        adapter.connect()
        assert adapter._conn is not None
        assert adapter._pool is not None

        adapter.close()
        assert adapter._conn is None
        assert adapter._pool is None

    def test_create_schema(self, pg_adapter):
        """Test creating database schema."""
        # Schema already created by fixture, verify tables exist
        tables = pg_adapter.get_tables()
        expected_tables = [
            "author_influences",
            "author_movements",
            "authors",
            "book_authors",
            "book_subjects",
            "books",
            "enrichment_log",
            "literary_movements",
            "manual_tags",
            "metadata",
            "notes",
            "subjects",
        ]
        assert sorted(tables) == expected_tables

    def test_get_table_schema(self, pg_adapter):
        """Test getting table schema information."""
        schema = pg_adapter.get_table_schema("books")
        assert len(schema) > 0

        # Check for expected columns
        column_names = [col["name"] for col in schema]
        assert "id" in column_names
        assert "title" in column_names

    def test_execute_and_fetchone(self, pg_adapter):
        """Test executing query and fetching one result."""
        # Insert test data (note: ? placeholders are auto-converted to %s)
        pg_adapter.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            ("test_key", "test_value"),
        )
        pg_adapter.commit()

        # Fetch the data
        result = pg_adapter.fetchone("SELECT key, value FROM metadata WHERE key = ?", ("test_key",))
        assert result is not None
        assert result["key"] == "test_key"
        assert result["value"] == "test_value"

    def test_execute_and_fetchall(self, pg_adapter):
        """Test executing query and fetching all results."""
        # Insert multiple rows
        pg_adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("key1", "value1"))
        pg_adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("key2", "value2"))
        pg_adapter.commit()

        # Fetch all
        results = pg_adapter.fetchall("SELECT key, value FROM metadata ORDER BY key")
        assert len(results) == 2
        assert results[0]["key"] == "key1"
        assert results[1]["key"] == "key2"

    def test_commit_and_rollback(self, pg_adapter):
        """Test transaction commit and rollback."""
        # Test commit
        pg_adapter.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)", ("commit_test", "value")
        )
        pg_adapter.commit()

        result = pg_adapter.fetchone("SELECT value FROM metadata WHERE key = ?", ("commit_test",))
        assert result is not None

        # Test rollback
        pg_adapter.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            ("rollback_test", "value"),
        )
        pg_adapter.rollback()

        result = pg_adapter.fetchone("SELECT value FROM metadata WHERE key = ?", ("rollback_test",))
        assert result is None

    def test_integrity_error(self, pg_adapter):
        """Test that integrity errors are properly raised."""
        # Insert a row with primary key
        pg_adapter.execute("INSERT INTO metadata (key, value) VALUES (?, ?)", ("pk_test", "value1"))
        pg_adapter.commit()

        # Try to insert duplicate primary key
        with pytest.raises(IntegrityError):
            pg_adapter.execute(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                ("pk_test", "value2"),
            )

    def test_placeholder_property(self, pg_config):
        """Test placeholder property."""
        adapter = PostgreSQLAdapter(**pg_config)
        assert adapter.placeholder == "%s"

    def test_cursor_method(self, pg_adapter):
        """Test getting raw cursor."""
        cursor = pg_adapter.cursor()
        assert cursor is not None

    def test_placeholder_conversion(self, pg_adapter):
        """Test that ? placeholders are converted to %s for PostgreSQL."""
        # This query uses ? placeholders but should work with PostgreSQL
        pg_adapter.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            ("conversion_test", "value"),
        )
        pg_adapter.commit()

        result = pg_adapter.fetchone(
            "SELECT value FROM metadata WHERE key = ?", ("conversion_test",)
        )
        assert result is not None
        assert result["value"] == "value"


class TestPostgreSQLDatabaseFactory:
    """Tests for PostgreSQL database factory."""

    def test_create_postgresql_from_config(self):
        """Test creating PostgreSQL adapter from config."""
        config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
        )

        adapter = create_database(config)
        assert isinstance(adapter, PostgreSQLAdapter)
        assert adapter.host == "localhost"
        assert adapter.port == 5432

    def test_config_validates_postgresql_requirements(self):
        """Test that config validates PostgreSQL requirements."""
        with pytest.raises(ValueError, match="host, database, and user are required"):
            DatabaseConfig(db_type="postgresql")

    def test_config_sets_default_port(self):
        """Test that config sets default PostgreSQL port."""
        config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            database="test_db",
            user="test_user",
        )
        assert config.port == 5432

    def test_config_accepts_pool_settings(self):
        """Test that config accepts pool size settings."""
        config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            database="test_db",
            user="test_user",
            pool_size=10,
            pool_max_overflow=20,
        )
        assert config.pool_size == 10
        assert config.pool_max_overflow == 20
