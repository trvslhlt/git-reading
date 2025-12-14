"""Shared constants for the git-reading application.

For environment-based configuration (database settings, etc.), use the env module:
    from common.env import env
    db_type = env.database_type()
"""

from pathlib import Path

# Data directories
DATA_DIR = Path("./data")
INDEX_DIR = DATA_DIR / "index"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
DATABASE_PATH = DATA_DIR / "readings.db"

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
