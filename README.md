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
make postgres-install  # Install PostgreSQL dependencies (default backend)
```

### Quick Start

#### Database Setup (PostgreSQL)

```bash
# Start PostgreSQL via Docker
make postgres-up

# Create .env file (optional - defaults work for local development)
cp .env.example .env
```

#### Extract and Load Data

```bash
# Extract reading notes (incremental by default)
make run-extract ARGS='--notes-dir /path/to/notes'

# Force full re-extraction
make run-extract ARGS='--notes-dir /path/to/notes --full'

# For all available commands
make help
```

Run any command with `ARGS='--help'` for detailed options.

**Note**: As of v2.0, extraction uses an incremental approach with an append-only log in `./index/` directory. See [Breaking Changes](#breaking-changes) below.

### Semantic Search

AI-powered semantic search through your notes using local embeddings:

```bash
make search  # One-command setup and index building
make run-search-query ARGS='"meaning of life"'
```

See [docs/SEMANTIC_SEARCH.md](docs/SEMANTIC_SEARCH.md) for architecture and advanced features.

### Database Backends

Git-reading supports two database backends:
- **PostgreSQL** (default): Production-ready with connection pooling
- **SQLite**: Simple file-based fallback

Set `DATABASE_TYPE=sqlite` in `.env` to use SQLite instead. See [docs/DATABASE.md](docs/DATABASE.md) for details.

### Metadata Enrichment

Automatically enrich your books and authors with metadata from external APIs:

```bash
# Check what's already enriched
make run-enrich-status

# Enrich books with ISBNs, publication info, subjects (Open Library)
make run-enrich ARGS='--sources openlibrary --limit 10'

# Enrich authors with biographical data, movements (Wikidata)
make run-enrich ARGS='--sources wikidata --entity-type authors --limit 5'

# Enrich everything from multiple sources
make run-enrich ARGS='--sources openlibrary wikidata --entity-type both'
```

**What gets enriched:**
- **Books**: ISBNs, publication year, subjects, literary movements, awards
- **Authors**: Birth/death dates & places, nationality, biography, movements

See [docs/ENRICHMENT_GUIDE.md](docs/ENRICHMENT_GUIDE.md) for complete reference.

### GraphQL API

Interactive GraphQL API for building custom visualizations and graph-based explorations:

```bash
# Quick start (auto-installs, launches, and opens browser)
make api

# Or install dependencies first
make api-install
make run-api  # Opens GraphQL Playground in browser
```

Access points (Playground opens automatically):
- **GraphQL Playground**: http://localhost:8000/graphql
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs

**Features:**
- Author-Book graph visualization queries
- Author search with partial matching
- Author influence network exploration
- Flexible GraphQL queries for custom views

**Documentation:**
- **[API Usage Guide](docs/API_USAGE.md)** - Examples with sample requests/responses
- [API README](src/api/README.md) - Complete API reference and schema

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

### Incremental Extraction

The extraction system now uses an **incremental approach** that only processes changed files:

- **First run**: Full extraction of all notes
- **Subsequent runs**: Only extract changes since last run
- **Output**: Append-only log in `./index/` directory
- **Performance**: O(m) where m = changed files (vs O(n) for all files)

Each extraction creates a new file tracking add/update/delete operations:

```
index/
├── extraction_20251201_143022_abc123.json  # Full extraction
├── extraction_20251201_150500_def456.json  # Incremental update
└── extraction_20251201_152000_ghi789.json  # Incremental update
```

### Extraction File Format

Each extraction file contains:

```json
{
  "extraction_metadata": {
    "timestamp": "2025-12-01T15:20:00Z",
    "git_commit_hash": "abc123...",
    "extraction_type": "full|incremental",
    "previous_commit_hash": "def456..."
  },
  "items": [
    {
      "item_id": "sha256:...",
      "operation": "add|update|delete",
      "book_title": "Book Title",
      "author_first_name": "Firstname",
      "author_last_name": "Lastname",
      "section": "notes",
      "content": "Note content",
      "source_file": "lastname__firstname.md",
      "date_read": "2024-03-15"
    }
  ]
}
```

### Breaking Changes (v2.0)

**Incremental extraction introduces breaking changes:**

#### CLI Changes
- **Removed**: `--output book_index.json` option
- **New**: `--index-dir ./index` (default directory for extraction files)
- **New**: `--full` flag to force full re-extraction
- **Default**: Incremental extraction (not full)

#### Old Commands (v1.x)
```bash
extract readings --notes-dir ./notes --output book_index.json
```

#### New Commands (v2.0+)
```bash
# Incremental extraction (default)
extract readings --notes-dir ./notes

# Full re-extraction
extract readings --notes-dir ./notes --full

# Custom index directory
extract readings --notes-dir ./notes --index-dir ./custom_index
```

#### Output Format Changes
- **Old**: Single `book_index.json` file (book-centric)
- **New**: Multiple extraction files in `index/` directory (item-centric, append-only log)

#### Migration Steps
1. Run full extraction: `extract readings --notes-dir ./notes --full`
2. **Important**: Downstream consumers (search, load) need updates to read from `index/` directory
3. Delete old `book_index.json` file

See [docs/INCREMENTAL_EXTRACTION_PLAN.md](docs/INCREMENTAL_EXTRACTION_PLAN.md) for detailed architecture.

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

The extraction system uses git as the source of truth for change detection:

1. **First run**: Parses all markdown files, extracts items, marks all as "add"
2. **Subsequent runs**:
   - Runs `git diff` to find changed files since last extraction
   - For added files: extract and mark all as "add"
   - For modified files: extract current + previous (via `git show`), compare
   - For deleted files: extract previous (via `git show`), mark all as "delete"
3. **Item IDs**: Each item gets a deterministic SHA256 ID based on book + author + section + content
4. **Output**: Append-only extraction files with operation types (add/update/delete)

The `--git-dir` parameter allows separation of git repository and notes directory.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system architecture and [docs/INCREMENTAL_EXTRACTION_PLAN.md](docs/INCREMENTAL_EXTRACTION_PLAN.md) for detailed design.
