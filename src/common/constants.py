"""Shared constants for the git-reading application."""

import os
from pathlib import Path

# Data directories
DATA_DIR = Path("./data")
INDEX_DIR = DATA_DIR / "index"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
DATABASE_PATH = DATA_DIR / "readings.db"

# Database configuration (can be overridden by environment variables)
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")

# SQLite configuration (used when DATABASE_TYPE=sqlite)
SQLITE_DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATABASE_PATH)))

# PostgreSQL configuration (used when DATABASE_TYPE=postgresql)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "git_reading")
POSTGRES_USER = os.getenv("POSTGRES_USER", "git_reading_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "5"))
POSTGRES_POOL_MAX_OVERFLOW = int(os.getenv("POSTGRES_POOL_MAX_OVERFLOW", "10"))

# Canonical section names that should be used in markdown reading notes
# These are section headers (## Section Name) that should not be mistaken for book titles
CANONICAL_SECTIONS: set[str] = {
    "excerpts",
    "ideas",
    "images",
    "notes",
    "representations",
    "same time",
    "terms",
    "threads",
    "themes",
}
