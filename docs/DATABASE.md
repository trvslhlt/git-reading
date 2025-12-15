# Database Loading Guide

This guide explains how to load data from extraction files into database storage.

## Database Backend Support

Git-reading supports two database backends:

- **PostgreSQL** (default): Production-ready, scalable, with connection pooling
- **SQLite**: Simple, file-based, zero-configuration fallback

Both backends provide the same functionality through a unified adapter interface.

## Why Use a Database?

Database storage provides several advantages over JSON files:

1. **Structured Queries**: Use SQL to query books, authors, genres, and relationships
2. **Better Performance**: Indexed lookups for filtering and joins
3. **Easy Enrichment**: Add metadata from external APIs without restructuring
4. **Graph Exploration**: Built-in support for relationships (author influences, genre hierarchies)
5. **Scalability**: Handles larger datasets more efficiently

## Database Schema

The database includes the following tables:

### Core Tables

- **books**: Book metadata (title, ISBN, publication year, ratings, etc.)
- **authors**: Author information (name, birth/death years, nationality, bio)
- **chunks**: Text excerpts with references to their FAISS vector positions
- **genres**: Genre/subject taxonomy with hierarchical support
- **book_authors**: Many-to-many relationship between books and authors
- **book_genres**: Many-to-many relationship between books and genres
- **author_influences**: Graph of author influences for exploration

### Key Features

- Foreign key constraints maintain referential integrity
- Indexes on common join columns for fast queries
- Support for multiple authors per book
- Hierarchical genre taxonomy (parent_id)
- Ready for enrichment with external metadata

## Choosing a Database Backend

### PostgreSQL (Default)

PostgreSQL provides better performance and scalability.

#### Setup

1. **Start PostgreSQL** (via Docker):
   ```bash
   make postgres-up
   ```

2. **Install PostgreSQL dependencies**:
   ```bash
   make postgres-install
   ```

3. **Configure environment variables** (create a `.env` file):
   ```bash
   cp .env.example .env
   ```

   Edit `.env` if needed (defaults are fine for local development):
   ```bash
   DATABASE_TYPE=postgresql  # Default
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=git_reading
   POSTGRES_USER=git_reading_user
   POSTGRES_PASSWORD=dev_password
   ```

4. **Load data**:
   ```bash
   make run-load ARGS='--index-dir data/index --database readings'
   ```

#### Docker Commands

```bash
make postgres-up       # Start PostgreSQL container
make postgres-down     # Stop PostgreSQL (preserves data)
make postgres-logs     # View container logs
make postgres-status   # Check health
make postgres-psql     # Open PostgreSQL CLI
make postgres-clean    # Remove container and data (with confirmation)
```

### SQLite (Fallback)

SQLite requires no setup and works out of the box:

```bash
# Switch to SQLite
export DATABASE_TYPE=sqlite
make run-load ARGS='--index-dir data/index --database data/readings.db'
```

No dependencies needed - just specify the database file path.

## Loading Process

### Step 1: Load the Data

The `--database` argument is interpreted based on your `DATABASE_TYPE` setting:
- **PostgreSQL**: Provide database name (e.g., `readings`)
- **SQLite**: Provide file path (e.g., `data/readings.db`)

```bash
# PostgreSQL (default) - use database name
make run-load ARGS='--index-dir data/index --database readings'

# SQLite - use file path
export DATABASE_TYPE=sqlite
make run-load ARGS='--index-dir data/index --database data/readings.db'

# Force overwrite existing data
make run-load ARGS='--index-dir data/index --database readings --force'

# Incremental update
make run-load ARGS='--index-dir data/index --database readings --incremental'
```

**Note**:
- For **SQLite**, `--force` deletes and recreates the database file
- For **PostgreSQL**, `--force` drops and recreates all tables in the existing database

### Step 2: Verify Load

The loading process automatically verifies:
- All notes were loaded
- FAISS indices are sequential (0, 1, 2, ...)
- Note counts match between sources and database

Output:
```
Loading data from .tmp/index.json...
Found 201 books
Extracted 4174 chunks from books
Creating database at .tmp/readings.db...
Loading data...
  Processed 500/4174 chunks...
  ...
Load complete!
  Books: 199
  Authors: 126
  Chunks: 4174
✅ Load verification passed
```

## What Gets Loaded?

### From JSON Structure

```json
{
  "books": [
    {
      "title": "American Pastoral",
      "author": "Philip Roth",
      "sections": {
        "excerpts": ["text1", "text2"],
        "notes": ["note1", "note2"]
      }
    }
  ]
}
```

### To Database Structure

**Books Table**:
```
id: "philip-roth_american-pastoral"
title: "American Pastoral"
```

**Authors Table**:
```
id: "philip-roth"
name: "Philip Roth"
```

**Book_Authors Table** (Junction):
```
book_id: "philip-roth_american-pastoral"
author_id: "philip-roth"
```

**Chunks Table**:
```
id: 1
book_id: "philip-roth_american-pastoral"
section: "excerpts"
excerpt: "text1"
faiss_index: 0  <-- Position in FAISS vector store
```

## Querying the Database

### Example Queries

```sql
-- Get all books by an author
SELECT b.title, b.publication_year
FROM books b
JOIN book_authors ba ON b.id = ba.book_id
JOIN authors a ON ba.author_id = a.id
WHERE a.name = 'Philip Roth';

-- Count chunks per section
SELECT section, COUNT(*) as count
FROM chunks
GROUP BY section
ORDER BY count DESC;

-- Get all excerpts from a specific book
SELECT excerpt FROM chunks c
JOIN books b ON c.book_id = b.id
WHERE b.title = 'American Pastoral'
AND c.section = 'excerpts';

-- Find books with most excerpts
SELECT b.title, a.name, COUNT(*) as excerpt_count
FROM chunks c
JOIN books b ON c.book_id = b.id
JOIN book_authors ba ON b.id = ba.book_id
JOIN authors a ON ba.author_id = a.id
WHERE c.section = 'excerpts'
GROUP BY b.id, b.title, a.name
ORDER BY excerpt_count DESC
LIMIT 10;
```

### Using Python

```python
from load.db_schema import get_connection

# Connect to database
conn = get_connection('.tmp/readings.db')
cursor = conn.cursor()

# Query authors
cursor.execute("SELECT name FROM authors ORDER BY name")
for row in cursor.fetchall():
    print(row['name'])

conn.close()
```

## Integration with Vector Search

The `chunks` table includes a `faiss_index` column that maps to positions in the FAISS vector store:

- **chunks.faiss_index = 0** → First embedding in FAISS
- **chunks.faiss_index = 1** → Second embedding in FAISS
- etc.

This enables efficient vector search with SQL-based filtering:

1. Filter chunks using SQL (by author, book, section, genre)
2. Extract only the relevant FAISS indices
3. Search only the filtered embeddings (pre-filtering)
4. Return rich metadata from the database

## Next Steps

After loading, you can:

1. **Enrich the Data**: Add metadata from external APIs
   - ISBNs, publication years, ratings from Open Library
   - Author biographies from Wikipedia
   - Genre classifications from subject APIs

2. **Build Graph Features**: Populate relationships
   - Author influences
   - Genre hierarchies
   - Book recommendations

3. **Explore with SQL**: Query patterns in your reading
   - Most read authors
   - Favorite genres
   - Reading trends over time

4. **Vector Search**: Use the query module for semantic search of your notes

## Testing

### Running Tests

The test suite includes both unit tests and integration tests:

```bash
# Run all tests (PostgreSQL integration tests skipped by default)
make test

# Run with PostgreSQL integration tests (requires running PostgreSQL)
make postgres-up  # Start PostgreSQL
RUN_POSTGRES_TESTS=1 make test
```

**Test breakdown:**
- **Unit tests** (20 tests): Always run, no database required
  - SQLite adapter tests (11 tests)
  - Database factory tests (5 tests)
  - PostgreSQL factory tests (4 tests - no database needed)

- **Integration tests** (11 tests): Require `RUN_POSTGRES_TESTS=1`
  - PostgreSQL adapter tests (11 tests - require running database)

## Troubleshooting

### Load fails: "Index directory not found"

Make sure you've extracted readings first:
```bash
make run-extract
```

### Database already exists

Use `--force` to overwrite:
```bash
make run-load ARGS='--force'
```

### Verification fails

Check the error message. Common issues:
- Corrupted JSON file
- Unexpected data structure
- Disk space issues

### PostgreSQL connection fails

Check that PostgreSQL is running and accessible:
```bash
make postgres-status  # Check Docker container status
make postgres-logs    # View PostgreSQL logs
```

Verify your `.env` file has correct credentials (copy from `.env.example` if needed).

## File Locations

- **Schema**: [src/load/db_schema.py](../src/load/db_schema.py)
- **Loading**: [src/load/load_data.py](../src/load/load_data.py)
- **CLI**: [src/load/cli.py](../src/load/cli.py)
- **Vector Search**: [src/query/vector_store.py](../src/query/vector_store.py)
