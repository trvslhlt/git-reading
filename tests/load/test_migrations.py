"""Tests for database migration system."""

import tempfile
from pathlib import Path

import pytest

from load.db import DatabaseConfig, create_database
from load.db.migrations import MigrationRunner


class TestMigrationRunner:
    """Test migration runner functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        config = DatabaseConfig(db_type="sqlite", db_path=db_path)
        adapter = create_database(config)

        yield adapter

        # Cleanup
        adapter.close()
        if db_path.exists():
            db_path.unlink()

    def test_ensure_migration_table(self, temp_db):
        """Test that migration table is created."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        runner.ensure_migration_table()

        # Check table exists
        tables = temp_db.get_tables()
        assert "schema_version" in tables

        # Check schema
        schema = temp_db.get_table_schema("schema_version")
        columns = {col["name"] for col in schema}
        assert "version" in columns
        assert "name" in columns
        assert "applied_at" in columns

        temp_db.close()

    def test_get_current_version_empty(self, temp_db):
        """Test getting version from empty database."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        version = runner.get_current_version()
        assert version == 0

        temp_db.close()

    def test_get_current_version_with_migrations(self, temp_db):
        """Test getting version after applying migrations."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        # Apply a migration manually
        runner.ensure_migration_table()
        temp_db.execute(
            f"INSERT INTO schema_version (version, name) VALUES ({temp_db.placeholder}, {temp_db.placeholder})",
            (1, "test_migration"),
        )
        temp_db.commit()

        version = runner.get_current_version()
        assert version == 1

        temp_db.close()

    def test_apply_migration(self, temp_db):
        """Test applying a single migration."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        # Create a test migration
        migrations_dir = runner.migrations_dir
        migrations_dir.mkdir(parents=True, exist_ok=True)

        test_migration = migrations_dir / "999_test_migration.sql"
        test_migration.write_text(
            """
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            """
        )

        try:
            # Apply migration
            runner.apply_migration(999, "test_migration", test_migration)

            # Check table was created
            tables = temp_db.get_tables()
            assert "test_table" in tables

            # Check migration was recorded
            result = temp_db.fetchone("SELECT * FROM schema_version WHERE version = ?", (999,))
            assert result is not None
            assert result["name"] == "test_migration"

        finally:
            # Cleanup
            test_migration.unlink()
            temp_db.close()

    def test_run_migrations_empty(self, temp_db):
        """Test running migrations when none are pending."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        # Clear migrations directory
        if runner.migrations_dir.exists():
            for f in runner.migrations_dir.glob("*.sql"):
                f.unlink()

        applied = runner.run_migrations()
        assert applied == 0

        temp_db.close()

    def test_run_migrations_with_pending(self, temp_db):
        """Test running migrations with pending migrations."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        # Create test migrations
        migrations_dir = runner.migrations_dir
        migrations_dir.mkdir(parents=True, exist_ok=True)

        migration1 = migrations_dir / "998_create_table1.sql"
        migration1.write_text("CREATE TABLE IF NOT EXISTS table1 (id INTEGER PRIMARY KEY);")

        migration2 = migrations_dir / "999_create_table2.sql"
        migration2.write_text("CREATE TABLE IF NOT EXISTS table2 (id INTEGER PRIMARY KEY);")

        try:
            # Run migrations
            applied = runner.run_migrations()
            assert applied == 2

            # Check tables were created
            tables = temp_db.get_tables()
            assert "table1" in tables
            assert "table2" in tables

            # Check version
            version = runner.get_current_version()
            assert version == 999

            # Run again - should be no pending migrations
            applied = runner.run_migrations()
            assert applied == 0

        finally:
            # Cleanup
            migration1.unlink()
            migration2.unlink()
            temp_db.close()

    def test_migration_ordering(self, temp_db):
        """Test that migrations are applied in correct order."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        # Create test migrations in wrong order
        migrations_dir = runner.migrations_dir
        migrations_dir.mkdir(parents=True, exist_ok=True)

        migration3 = migrations_dir / "997_third.sql"
        migration3.write_text("SELECT 3;")

        migration1 = migrations_dir / "995_first.sql"
        migration1.write_text("SELECT 1;")

        migration2 = migrations_dir / "996_second.sql"
        migration2.write_text("SELECT 2;")

        try:
            # Get pending migrations
            pending = runner.get_pending_migrations()

            # Check order
            assert len(pending) == 3
            assert pending[0][0] == 995
            assert pending[1][0] == 996
            assert pending[2][0] == 997

        finally:
            # Cleanup
            migration1.unlink()
            migration2.unlink()
            migration3.unlink()
            temp_db.close()

    def test_migration_rollback_on_error(self, temp_db):
        """Test that failed migrations are rolled back."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        # Create a migration that will fail
        migrations_dir = runner.migrations_dir
        migrations_dir.mkdir(parents=True, exist_ok=True)

        bad_migration = migrations_dir / "994_bad_migration.sql"
        bad_migration.write_text("INVALID SQL SYNTAX;")

        try:
            # Try to apply migration - should fail
            with pytest.raises(Exception):
                runner.apply_migration(994, "bad_migration", bad_migration)

            # Check migration was not recorded
            result = temp_db.fetchone("SELECT * FROM schema_version WHERE version = ?", (994,))
            assert result is None

        finally:
            # Cleanup
            bad_migration.unlink()
            temp_db.close()

    def test_skip_invalid_filenames(self, temp_db):
        """Test that invalid migration filenames are skipped."""
        temp_db.connect()
        runner = MigrationRunner(temp_db)

        # Create migrations with invalid filenames
        migrations_dir = runner.migrations_dir
        migrations_dir.mkdir(parents=True, exist_ok=True)

        invalid1 = migrations_dir / "no_version.sql"
        invalid1.write_text("SELECT 1;")

        invalid2 = migrations_dir / "abc_not_a_number.sql"
        invalid2.write_text("SELECT 2;")

        valid = migrations_dir / "993_valid_migration.sql"
        valid.write_text("SELECT 3;")

        try:
            # Get pending migrations
            pending = runner.get_pending_migrations()

            # Should only have the valid one
            assert len(pending) == 1
            assert pending[0][0] == 993

        finally:
            # Cleanup
            invalid1.unlink()
            invalid2.unlink()
            valid.unlink()
            temp_db.close()


class TestDatabaseAdapterMigrations:
    """Test migration integration with database adapters."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        config = DatabaseConfig(db_type="sqlite", db_path=db_path)
        adapter = create_database(config)

        yield adapter

        # Cleanup
        adapter.close()
        if db_path.exists():
            db_path.unlink()

    def test_run_migrations_method(self, temp_db):
        """Test run_migrations method on adapter."""
        temp_db.connect()

        # Create schema first
        temp_db.create_schema()

        # Run migrations
        applied = temp_db.run_migrations()

        # Should apply initial migration
        assert applied >= 0

        # Check migration table exists
        tables = temp_db.get_tables()
        assert "schema_version" in tables

        temp_db.close()

    def test_migrations_idempotent(self, temp_db):
        """Test that migrations can be run multiple times safely."""
        temp_db.connect()
        temp_db.create_schema()

        # Run migrations twice
        temp_db.run_migrations()
        applied2 = temp_db.run_migrations()

        # Second run should apply no new migrations
        assert applied2 == 0

        temp_db.close()
