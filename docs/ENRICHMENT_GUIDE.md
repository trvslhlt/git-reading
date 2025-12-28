# Enrichment Quick Reference Guide

This guide provides practical examples for enriching book and author metadata in git-reading.

## Quick Start

### Check Current Status
```bash
make run-enrich-status
```

This shows:
- Total books and authors in database
- Percentage enriched with ISBNs, publication years, subjects, etc.
- Enrichment activity by source and method

### Enrich Books Only

**From Open Library** (ISBNs, publication info, subjects):
```bash
# Test with 10 books
make run-enrich ARGS='--sources openlibrary --limit 10'

# Enrich all unenriched books
make run-enrich ARGS='--sources openlibrary'
```

**From Wikidata** (subjects, literary movements, awards):
```bash
# Test with 5 books
make run-enrich ARGS='--sources wikidata --limit 5'

# Enrich all unenriched books
make run-enrich ARGS='--sources wikidata'
```

**From Both Sources**:
```bash
make run-enrich ARGS='--sources openlibrary wikidata --limit 10'
```

### Enrich Authors Only

**From Wikidata** (biographical data, literary movements):
```bash
# Test with 5 authors
make run-enrich ARGS='--sources wikidata --entity-type authors --limit 5'

# Enrich all unenriched authors
make run-enrich ARGS='--sources wikidata --entity-type authors'
```

### Enrich Both Books and Authors

```bash
# Test with 5 of each
make run-enrich ARGS='--sources wikidata --entity-type both --limit 5'

# Enrich everything
make run-enrich ARGS='--sources wikidata --entity-type both'
```

## What Gets Enriched?

### Books

**Open Library provides:**
- ISBN-10 and ISBN-13
- Publication year
- Publisher
- Page count
- Language
- Description
- Subjects/genres
- Cover image URLs

**Wikidata provides:**
- Subjects and genres (with human-readable labels)
- Literary movements (e.g., "Modernism", "Science Fiction")
- Awards (e.g., "Hugo Award", "Pulitzer Prize")
- Additional ISBNs and publication data

### Authors

**Wikidata provides:**
- Birth year and place (e.g., 1903, "London")
- Death year and place
- Nationality (e.g., "United Kingdom")
- Biography/description
- Wikipedia URL
- VIAF identifier (library standard)
- Literary movements (e.g., "Bloomsbury Group")

## Advanced Usage

### Incremental Enrichment

The system automatically skips already-enriched items:
- Books with `isbn_13 IS NOT NULL` are skipped for Open Library
- Books/authors with `wikidata_id IS NOT NULL` are skipped for Wikidata

To re-enrich, you would need to manually clear the relevant fields in the database.

### Export Enriched Data

Export to CSV for review:
```bash
make run-enrich-export ARGS='--output enriched_books.csv'
```

Export to JSON:
```bash
make run-enrich-export ARGS='--output enriched_books.json --format json'
```

### View Help

```bash
make run-enrich ARGS='--help'
```

## Understanding the Output

During enrichment, you'll see output like:

```
[1/10] Enriching 'Neuromancer' by William Gibson
✓ Open Library: ISBN-13: 978-0441569595, Year: 1984, Subjects: 5
✓ Wikidata: ID: Q232142, Subjects: 3, Movements: 1, Awards: 2

Book enrichment stats:
  Attempted: 10
  Successful: 8
  Failed: 2
  Skipped: 0
```

- **Attempted**: Total number tried
- **Successful**: Successfully enriched from at least one source
- **Failed**: No data found or API error
- **Skipped**: Already enriched (has required ID field)

## Database Schema

### New Tables (Phase 2.1)

**Literary Movements:**
- `literary_movements` - Movement details (name, description, era)
- `book_movements` - Links books to movements
- `author_movements` - Links authors to movements

**Awards:**
- `awards` - Award details (name, category, year established)
- `book_awards` - Links books to awards (with year won)

### Key Fields

**Books:**
- `wikidata_id` - Wikidata entity ID (e.g., "Q232142")
- `openlibrary_id` - Open Library work ID (e.g., "/works/OL45804W")
- `isbn_13` - Primary ISBN identifier

**Authors:**
- `wikidata_id` - Wikidata entity ID (e.g., "Q42")
- `viaf_id` - Virtual International Authority File ID
- `wikipedia_url` - English Wikipedia page URL

## Q-ID Resolution

Wikidata uses Q-IDs (like "Q84" for London). The system automatically converts these to human-readable labels:

**Before Resolution:**
```json
{
  "birth_place": "Q84",
  "subjects": ["Q24925", "Q8261"]
}
```

**After Resolution:**
```json
{
  "birth_place": "London",
  "subjects": ["Science fiction", "Novel"]
}
```

This happens automatically during enrichment using batch API calls with caching for efficiency.

## Troubleshooting

### No matches found

**For books:**
- Wikidata has lower coverage than Open Library for books
- Try using both sources: `--sources openlibrary wikidata`
- Some books may not exist in either database

**For authors:**
- Ensure the author name matches what's in the database
- Check author names with: `sqlite3 data/books.db "SELECT name FROM authors LIMIT 10"`

### API timeouts

If you get timeout errors:
- Use `--limit` to process fewer items at once
- Wait a few minutes and retry
- Wikidata's SPARQL endpoint can be slow during peak times

### Rate limiting

Both APIs have rate limits:
- Open Library: 100 requests/5 minutes (automatically handled)
- Wikidata: 60 requests/minute (automatically handled)

The system includes automatic rate limiting, but if you see errors, add a delay between batches.

## Integration with Other Commands

### Full Workflow

1. **Extract notes** from markdown files:
   ```bash
   make run-extract ARGS='--notes-dir readings'
   ```

2. **Load to database**:
   ```bash
   make run-load ARGS='--index-dir data/index'
   ```

3. **Enrich metadata**:
   ```bash
   make run-enrich ARGS='--sources openlibrary wikidata --entity-type both'
   ```

4. **Build search index**:
   ```bash
   make search
   ```

5. **Launch visualization**:
   ```bash
   make streamlit
   ```

## Migration Scripts

If you're upgrading from an earlier version, run migrations:

```bash
# Add book_movements table
sqlite3 data/books.db < migrations/001_add_book_movements.sql

# Add awards tables
sqlite3 data/books.db < migrations/002_add_awards.sql
```

These are safe to run multiple times (uses `CREATE TABLE IF NOT EXISTS`).

## See Also

- [ENRICHMENT_ROADMAP.md](ENRICHMENT_ROADMAP.md) - Full roadmap and technical details
- [Makefile](../Makefile) - All available commands
- `make run-enrich ARGS='--help'` - Complete CLI reference
