# Git Reading

A Python tool for indexing reading notes from markdown files, using git history to track when books were read.

## For Users

### Overview

This tool scans markdown files containing book notes and extracts structured information about each book: titles, authors, reading dates, and organized sections. The output is a queryable JSON index that preserves your reading timeline.

### Prerequisites

- Python 3.10+
- Git
- [Make](https://www.gnu.org/software/make/)
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
make install
```

### Quick Start

```bash
# Extract reading notes
make run-extract ARGS='--notes-dir /path/to/notes --output book_index.json'

# For all available commands
make help
```

Run any command with `ARGS='--help'` for detailed options.

### Semantic Search

AI-powered semantic search through your notes using local embeddings:

```bash
make search  # One-command setup and index building
make run-search-query ARGS='"meaning of life"'
```

See [docs/SEMANTIC_SEARCH.md](docs/SEMANTIC_SEARCH.md) for architecture and advanced features.

### Visualization

Interactive dashboard for exploring your indexed books:

```bash
make streamlit  # One-command setup and launch
```

Opens at `http://localhost:8501`. See [streamlit_app/README.md](streamlit_app/README.md) for features.

### Markdown Format

Files should be named `lastname__firstname.md` (double underscore). Each file can contain multiple books:

```markdown
# Book Title

## notes
- Note item 1

## excerpts
- Quote from the book
```

Common sections: notes, excerpts, threads, terms, ideas.

### Output Format

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

---

## For Developers

### Setup

```bash
git clone <repo-url>
cd git-reading
make dev-install  # Installs dependencies and package
```

### Development

All development tasks are available via Make:

```bash
make help     # Show all available commands
make test     # Run tests
make format   # Format code with Ruff
make lint     # Lint code with Ruff
```

Use `make run-*` commands during development (no reinstall needed). Run `make install` to test the installed version.

### Architecture

The `src/` directory follows an ETL pattern with stages for extraction (`extract/`), normalization (`normalize_source/`), and querying (`query/`). Stubs exist for future enrichment, transformation, and loading stages. The `streamlit_app/` provides visualization separate from core pipeline code.

### Configuration

Tool configuration lives in `pyproject.toml`:
- **Ruff**: Line length, linting rules, formatter settings
- **Pytest**: Test discovery patterns
- **Build**: Hatchling with src layout

### How It Works

1. Scans markdown files for book titles (`#` headers) and sections (`##` headers)
2. Uses `git blame` to determine when each book was added
3. Outputs a JSON index sorted by reading date

The `--git-dir` parameter allows separation of git repository and notes directory.
