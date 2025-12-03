# Git Reading

A Python tool for indexing reading notes from markdown files, using git history to track when books were read.

## For Users

### Overview

This tool scans markdown files containing book notes and extracts structured information about each book:
- Book titles and authors (derived from filenames)
- Reading dates (based on when the book title was first added to git)
- Organized sections (notes, excerpts, threads, etc.)

The output is a queryable JSON index that preserves your reading timeline.

### Installation

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the tool
uv sync
```

### Usage

Index your reading notes:

```bash
uv run extract-readings --notes-dir /path/to/notes --output book_index.json
```

If your notes and git repository are in different locations:

```bash
uv run extract-readings --notes-dir /path/to/notes --git-dir /path/to/repo --output book_index.json
```

If run from the notes directory:

```bash
uv run extract-readings
```

#### Arguments

- `--notes-dir`: Directory containing markdown notes (default: current directory)
- `--git-dir`: Git repository directory for date tracking (default: auto-detect from notes-dir)
- `--output`: Output JSON file path (default: `book_index.json`)

### Markdown File Format

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

### Requirements

- Python 3.10+
- Git (for reading date tracking)

---

## For Developers

### Project Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management and Make for development tasks:

```bash
# Clone the repository
git clone <repo-url>
cd git-reading

# Install dependencies and the package
make dev-install
```

### Development Workflow

The project includes a Makefile for common development tasks:

```bash
# Run with current source code (no install needed - best for development)
make run ARGS="--notes-dir /path/to/notes --output index.json"

# Install the package (needed after making changes to test installed version)
make install

# Run tests
make test

# Format code
make format

# Lint code
make lint

# Clean build artifacts
make clean

# Show all available commands
make help
```

**Key tip**: Use `make run` during development to run your current source code without reinstalling. This bypasses the uv `.pth` file limitation.

### Project Structure

```
git-reading/
├── src/
│   ├── extract/            # Extract data from markdown files
│   │   ├── __init__.py
│   │   └── main.py         # Main extraction logic (entry point)
│   ├── normalize_source/   # Normalize source data
│   │   └── __init__.py
│   ├── enrich/             # Enrich data with additional info
│   │   └── __init__.py
│   ├── transform/          # Transform data formats
│   │   └── __init__.py
│   ├── load/               # Load data to destinations
│   │   └── __init__.py
│   └── query/              # Query indexed data
│       └── __init__.py
├── tests/
│   └── test_integration.py # Integration tests
├── Makefile                 # Development task automation
├── pyproject.toml           # Project config, dependencies, tool settings
├── pytest.ini               # Test configuration
└── .vscode/
    ├── settings.json        # VSCode editor settings
    └── extensions.json      # Recommended extensions
```

The architecture follows an ETL (Extract, Transform, Load) pattern with additional stages for normalization, enrichment, and querying.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test
uv run pytest tests/test_integration.py::test_basic_indexing_same_directory
```

### Code Quality

#### Formatting

We use [Ruff](https://github.com/astral-sh/ruff) for code formatting (Black-compatible):

```bash
# Format all code
uv run ruff format .

# Check formatting without making changes
uv run ruff format --check .
```

#### Linting

Ruff also handles linting with rules for code style, errors, and best practices:

```bash
# Lint code
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .
```

#### VSCode Integration

The project includes VSCode settings that automatically:
- Format code on save
- Organize imports
- Fix linting issues
- Show inline diagnostics

Install recommended extensions when prompted, or manually install:
- Python (`ms-python.python`)
- Ruff (`charliermarsh.ruff`)

### Configuration

All tool configuration lives in `pyproject.toml`:
- **Ruff**: Line length (100), linting rules, formatter settings
- **Pytest**: Test discovery patterns
- **Build**: Hatchling with src layout

### How It Works

1. Scans markdown files in the specified directory
2. Extracts book titles (single `#` headers) and their sections (double `##` headers)
3. Uses `git blame` to determine when each book title was added to the repository
4. Outputs a JSON index sorted by reading date

The `--git-dir` parameter allows the git repository and notes directory to be separate, useful when notes are tracked in a different repository or subdirectory.
