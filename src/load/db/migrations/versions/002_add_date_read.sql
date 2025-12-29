-- Add date_read column to books table to enable temporal analysis
-- This allows tracking when books were read based on git commit history

-- Note: For databases created with schema v2+, this column already exists in base schema
-- For older databases, the column must be added manually before running this migration

-- This migration only creates the index, which is idempotent and works on both
-- SQLite and PostgreSQL. Column addition is handled by base schema for new databases.

-- Create index on date_read for efficient temporal queries (idempotent)
CREATE INDEX IF NOT EXISTS idx_books_date_read ON books(date_read);
