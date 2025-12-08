"""Shared constants for the git-reading application."""

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
