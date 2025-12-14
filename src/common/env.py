"""Environment configuration interface for git-reading.

This module provides a clean interface for accessing environment variables,
centralizing all environment variable access in one place.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Environment:
    """Interface for accessing environment configuration."""

    @staticmethod
    def database_type() -> str:
        """Get the database type (sqlite or postgresql).

        Returns:
            Database type, defaults to 'postgresql'
        """
        return os.getenv("DATABASE_TYPE", "postgresql")

    @staticmethod
    def database_path() -> Path:
        """Get the SQLite database file path.

        Returns:
            Path to SQLite database file, defaults to ./data/readings.db
        """
        return Path(os.getenv("DATABASE_PATH", "./data/readings.db"))

    @staticmethod
    def postgres_host() -> str:
        """Get PostgreSQL host.

        Returns:
            PostgreSQL host, defaults to 'localhost'
        """
        return os.getenv("POSTGRES_HOST", "localhost")

    @staticmethod
    def postgres_port() -> int:
        """Get PostgreSQL port.

        Returns:
            PostgreSQL port, defaults to 5432
        """
        return int(os.getenv("POSTGRES_PORT", "5432"))

    @staticmethod
    def postgres_database() -> str:
        """Get PostgreSQL database name.

        Returns:
            Database name, defaults to 'git_reading'
        """
        return os.getenv("POSTGRES_DB", "git_reading")

    @staticmethod
    def postgres_user() -> str:
        """Get PostgreSQL user.

        Returns:
            Database user, defaults to 'git_reading_user'
        """
        return os.getenv("POSTGRES_USER", "git_reading_user")

    @staticmethod
    def postgres_password() -> str:
        """Get PostgreSQL password.

        Returns:
            Database password, defaults to empty string
        """
        return os.getenv("POSTGRES_PASSWORD", "")

    @staticmethod
    def postgres_pool_size() -> int:
        """Get PostgreSQL connection pool size.

        Returns:
            Pool size, defaults to 5
        """
        return int(os.getenv("POSTGRES_POOL_SIZE", "5"))

    @staticmethod
    def postgres_pool_max_overflow() -> int:
        """Get PostgreSQL connection pool max overflow.

        Returns:
            Max overflow, defaults to 10
        """
        return int(os.getenv("POSTGRES_POOL_MAX_OVERFLOW", "10"))


# Singleton instance for convenient access
env = Environment()
