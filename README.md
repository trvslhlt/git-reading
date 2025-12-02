# Git Reading

A Python tool for indexing reading notes from markdown files, using git history to track when books were read.

## Overview

This tool scans markdown files containing book notes and extracts structured information about each book, including:
- Book titles and authors (derived from filenames)
- Reading dates (based on when the book title was first added to git)
- Organized sections (notes, excerpts, threads, etc.)

The output is a queryable JSON index that preserves the reading timeline.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates virtual environment automatically)
uv sync
```

## Usage

Index your reading notes:

```bash
uv run index-readings --notes-dir /path/to/notes --output book_index.json
```

If run from the notes directory:

```bash
uv run index-readings
```

Or run the script directly:

```bash
uv run python index_readings.py
```

### Arguments

- `--notes-dir`: Directory containing markdown notes (default: current directory)
- `--output`: Output JSON file path (default: `book_index.json`)

## Markdown File Format

The tool expects markdown files named in the format `lastname_firstname.md`. Each file can contain multiple books:

```markdown
# Book Title

## Notes
- Note item 1
- Note item 2

## Excerpts
- Quote from the book

# Another Book Title

## Threads
- Key theme or idea
```

Section headers (`## Section`) organize content within each book. Common sections include Notes, Excerpts, Threads, Terms, and Ideas.

## How It Works

1. Scans markdown files in the specified directory
2. Extracts book titles (single `#` headers) and their sections (double `##` headers)
3. Uses `git blame` to determine when each book title was added to the repository
4. Outputs a JSON index sorted by reading date

## Requirements

- Python 3.10+
- Git (for reading date tracking)
- Markdown notes in a git repository

## Output Format

The generated JSON includes:

```json
{
  "generated_at": "2025-12-01T...",
  "notes_directory": "/path/to/notes",
  "total_books": 42,
  "books": [
    {
      "title": "Book Title",
      "author": "Firstname Lastname",
      "date_read": "2024-03-15",
      "source_file": "lastname_firstname.md",
      "sections": {
        "notes": ["note 1", "note 2"],
        "excerpts": ["quote 1"]
      }
    }
  ]
}
```
