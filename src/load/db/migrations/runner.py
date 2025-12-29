"""Migration runner for database schema updates."""

from pathlib import Path
from typing import TYPE_CHECKING

from common.logger import get_logger

if TYPE_CHECKING:
    from load.db.interface import DatabaseAdapter

logger = get_logger(__name__)


class MigrationRunner:
    """Runs database migrations and tracks schema versions."""

    def __init__(self, adapter: "DatabaseAdapter"):
        """Initialize migration runner.

        Args:
            adapter: Database adapter instance
        """
        self.adapter = adapter
        self.migrations_dir = Path(__file__).parent / "versions"

    def ensure_migration_table(self) -> None:
        """Create schema_version table if it doesn't exist."""
        create_table = """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        self.adapter.execute(create_table)
        self.adapter.commit()

    def get_current_version(self) -> int:
        """Get current schema version.

        Returns:
            Current version number, or 0 if no migrations applied
        """
        self.ensure_migration_table()

        result = self.adapter.fetchone("SELECT MAX(version) as version FROM schema_version")

        if result and result["version"] is not None:
            return result["version"]
        return 0

    def get_pending_migrations(self) -> list[tuple[int, str, Path]]:
        """Get list of pending migrations.

        Returns:
            List of tuples: (version, name, filepath)
        """
        current_version = self.get_current_version()

        # Get all migration files
        if not self.migrations_dir.exists():
            return []

        migrations = []
        for filepath in sorted(self.migrations_dir.glob("*.sql")):
            # Parse filename: 001_migration_name.sql
            parts = filepath.stem.split("_", 1)
            if len(parts) != 2:
                logger.warning(f"Skipping invalid migration filename: {filepath.name}")
                continue

            try:
                version = int(parts[0])
                name = parts[1]
            except ValueError:
                logger.warning(f"Skipping invalid migration filename: {filepath.name}")
                continue

            if version > current_version:
                migrations.append((version, name, filepath))

        return sorted(migrations, key=lambda x: x[0])

    def apply_migration(self, version: int, name: str, filepath: Path) -> None:
        """Apply a single migration.

        Args:
            version: Migration version number
            name: Migration name
            filepath: Path to migration SQL file
        """
        logger.info(f"Applying migration {version}: {name}")

        # Ensure migration table exists
        self.ensure_migration_table()

        # Read migration SQL
        sql = filepath.read_text()

        # Execute migration
        try:
            self.adapter.execute(sql)

            # Record migration
            self.adapter.execute(
                f"INSERT INTO schema_version (version, name) VALUES ({self.adapter.placeholder}, {self.adapter.placeholder})",
                (version, name),
            )

            self.adapter.commit()
            logger.info(f"✓ Applied migration {version}: {name}")

        except Exception as e:
            self.adapter.rollback()
            logger.error(f"✗ Failed to apply migration {version}: {e}")
            raise

    def run_migrations(self) -> int:
        """Run all pending migrations.

        Returns:
            Number of migrations applied
        """
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return 0

        logger.info(f"Found {len(pending)} pending migration(s)")

        for version, name, filepath in pending:
            self.apply_migration(version, name, filepath)

        return len(pending)

    def create_migration(self, name: str, sql: str) -> Path:
        """Create a new migration file.

        Args:
            name: Migration name (will be slugified)
            sql: SQL content

        Returns:
            Path to created migration file
        """
        # Get next version number
        current_version = self.get_current_version()
        next_version = current_version + 1

        # Slugify name
        slug = name.lower().replace(" ", "_").replace("-", "_")

        # Create migrations directory if needed
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Create migration file
        filename = f"{next_version:03d}_{slug}.sql"
        filepath = self.migrations_dir / filename

        filepath.write_text(sql)
        logger.info(f"Created migration: {filename}")

        return filepath
