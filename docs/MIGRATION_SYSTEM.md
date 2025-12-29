# Database Migration System

## Overview

The git-reading project uses an automated database migration system to manage schema changes over time. This system ensures that databases can be upgraded smoothly as new features are added.

## Architecture

### Components

1. **MigrationRunner** ([src/load/db/migrations/runner.py](../src/load/db/migrations/runner.py))
   - Discovers and applies pending migrations
   - Tracks migration history in `schema_version` table
   - Provides rollback on migration failure

2. **Migration Files** ([src/load/db/migrations/versions/](../src/load/db/migrations/versions/))
   - SQL files containing schema updates
   - Named with pattern: `NNN_description.sql`
   - Applied in numerical order

3. **Base Schema** ([src/load/db/schema_*.sql](../src/load/db/))
   - Complete, current schema for new databases
   - Separate files for SQLite and PostgreSQL

### Migration Flow

```
New Database:
  create_schema() → run_migrations()
  │                 │
  │                 └─ Migrations are idempotent (no-op)
  └─ Creates full schema from SQL file

Existing Database:
  run_migrations()
  │
  ├─ Check schema_version table
  ├─ Find pending migrations
  ├─ Apply each migration
  └─ Record in schema_version
```

## Creating Migrations

### Step 1: Update Base Schema

First, update the base schema files to include your changes:

```sql
-- src/load/db/schema_sqlite.sql
ALTER TABLE books ADD COLUMN new_field TEXT;
CREATE INDEX idx_books_new_field ON books(new_field);
```

Do the same for `schema_postgresql.sql`.

### Step 2: Create Migration File

Create a new migration file with the next version number:

```bash
# Example: Create migration 004
cat > src/load/db/migrations/versions/004_add_new_field.sql << 'EOF'
-- Add new_field to books table
-- For databases created with schema v4+, this field already exists

-- Add column (handle both new and existing databases)
-- Note: This example is for PostgreSQL; SQLite requires different approach

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'books' AND column_name = 'new_field'
    ) THEN
        ALTER TABLE books ADD COLUMN new_field TEXT;
    END IF;
END $$;

-- Create index (idempotent)
CREATE INDEX IF NOT EXISTS idx_books_new_field ON books(new_field);
EOF
```

### Step 3: Test Migration

```bash
# Run migration tests
PYTHONPATH=src uv run pytest tests/load/test_migrations.py -v

# Test on actual database
make run-load ARGS='--index-dir data/index --incremental'
```

## Migration Best Practices

### 1. Idempotency

Migrations should be safe to run multiple times:

```sql
-- Good: Idempotent
CREATE TABLE IF NOT EXISTS my_table (...);
CREATE INDEX IF NOT EXISTS idx_my_field ON my_table(my_field);

-- Bad: Not idempotent
CREATE TABLE my_table (...);  -- Fails if table exists
ALTER TABLE books ADD COLUMN field TEXT;  -- Fails if column exists
```

### 2. Database Compatibility

Support both SQLite and PostgreSQL:

```sql
-- Tables and indexes work the same
CREATE TABLE IF NOT EXISTS my_table (...);
CREATE INDEX IF NOT EXISTS idx_field ON my_table(field);

-- Column additions require different approaches
-- Option A: Skip column additions (rely on base schema for new databases)
-- Option B: Use database-specific syntax (PostgreSQL DO blocks)
```

### 3. Migration Naming

Use descriptive names that indicate what the migration does:

```
001_baseline_schema.sql
002_add_date_read.sql
003_add_phase2_enrichment.sql
004_add_genre_weights.sql
```

### 4. One-Way Migrations

Migrations are one-way (forward only). There is no automatic rollback system. If you need to undo a migration:

1. Create a new migration that reverses the changes
2. Or, restore from a database backup

## Current Migrations

| Version | Name | Description |
|---------|------|-------------|
| 001 | baseline_schema | Marker for initial schema version |
| 002 | add_date_read | Adds date_read column to books for temporal analysis |
| 003 | add_phase2_enrichment | Adds enrichment tables (book_movements, awards, author_influences) |

## Schema Version Table

The `schema_version` table tracks applied migrations:

```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Example contents:

```
version | name                  | applied_at
--------|----------------------|-------------------------
1       | baseline_schema      | 2025-12-29 14:27:00
2       | add_date_read        | 2025-12-29 14:27:01
3       | add_phase2_enrichment| 2025-12-29 14:27:02
```

## Troubleshooting

### Migration Fails

If a migration fails:

1. The migration is rolled back (not recorded in `schema_version`)
2. Check the error message
3. Fix the migration SQL
4. Run migrations again

### Migrations Out of Sync

If migrations get out of sync with the actual schema:

```bash
# Option 1: Rebuild database from scratch
make run-load ARGS='--index-dir data/index --force'

# Option 2: Manually fix schema, then mark migration as applied
sqlite3 data/readings.db "
  INSERT INTO schema_version (version, name)
  VALUES (3, 'add_phase2_enrichment');
"
```

### Missing schema_version Table

If `schema_version` doesn't exist, it means no migrations have run yet:

```bash
# Just run the load command - it will create the table
make run-load ARGS='--index-dir data/index --incremental'
```

## Integration with Load Process

The migration system is automatically integrated into the data loading process:

```python
# src/load/load_data.py
with get_adapter() as adapter:
    adapter.create_schema()  # Create base schema

    logger.info("Checking for schema migrations...")
    migrations_applied = adapter.run_migrations()
    if migrations_applied > 0:
        logger.info(f"Applied {migrations_applied} migration(s)")

    # ... load data ...
```

This means migrations run automatically whenever you load data, whether for a new database or an incremental update.

## Legacy Migrations

Before the migration system existed, schema changes were applied manually using SQL files in `/migrations/`. These have been:

1. Consolidated into migration 003
2. Documented in [/migrations/README.md](../migrations/README.md)
3. Deprecated (do not use for new changes)

For details on the migration consolidation, see the [migrations/README.md](../migrations/README.md) file.
