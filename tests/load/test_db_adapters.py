"""Tests for database adapters."""

from pathlib import Path

import pytest

from load.db import (
    DatabaseConfig,
    DatabaseError,
    IntegrityError,
    SQLiteAdapter,
    create_database,
)


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
            "authors",
            "book_authors",
            "book_genres",
            "books",
            "genres",
            "metadata",
            "notes",
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
