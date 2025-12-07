# Database Migration Guide

This guide explains how to migrate from the JSON-based index to SQLite database storage.

## Why Migrate?

The SQLite database provides several advantages over the single JSON file:

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

## Migration Process

### Step 1: Run the Migration

```bash
# Migrate with defaults (.tmp/index.json → .tmp/readings.db)
make run-migrate

# Or specify custom paths
make run-migrate ARGS='--index /path/to/index.json --database /path/to/output.db'

# Force overwrite existing database
make run-migrate ARGS='--force'
```

### Step 2: Verify Migration

The migration automatically verifies:
- All chunks were migrated
- FAISS indices are sequential (0, 1, 2, ...)
- Chunk counts match between JSON and database

Output:
```
Loading data from .tmp/index.json...
Found 201 books
Extracted 4174 chunks from books
Creating database at .tmp/readings.db...
Migrating data...
  Processed 500/4174 chunks...
  ...
Migration complete!
  Books: 199
  Authors: 126
  Chunks: 4174
✅ Migration verification passed
```

## What Gets Migrated?

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

This allows the database-backed vector store ([src/query/vector_store_db.py](../src/query/vector_store_db.py)) to:

1. Filter chunks using SQL (by author, book, section, genre)
2. Extract only the relevant FAISS indices
3. Search only the filtered embeddings (pre-filtering)
4. Return rich metadata from the database

## Next Steps

After migration, you can:

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

4. **Vector Search**: Use [vector_store_db.py](../src/query/vector_store_db.py) for database-backed semantic search

## Troubleshooting

### Migration fails: "Index file not found"

Make sure you've extracted readings first:
```bash
make run-extract
```

### Database already exists

Use `--force` to overwrite:
```bash
make run-migrate ARGS='--force'
```

### Verification fails

Check the error message. Common issues:
- Corrupted JSON file
- Unexpected data structure
- Disk space issues

## File Locations

- **Schema**: [src/load/db_schema.py](../src/load/db_schema.py)
- **Migration**: [src/load/migrate_to_db.py](../src/load/migrate_to_db.py)
- **CLI**: [src/load/cli.py](../src/load/cli.py)
- **DB Vector Store**: [src/query/vector_store_db.py](../src/query/vector_store_db.py)
