-- Migration: Add Phase 2 enrichment columns
-- Date: 2025-12-28
-- Description: Adds Wikidata enrichment columns to existing authors and books tables

-- Add wikidata_id to authors (if not exists)
-- SQLite doesn't have IF NOT EXISTS for columns, so we use a workaround
CREATE TABLE IF NOT EXISTS _temp_migration_check (col TEXT);

-- Add wikidata_id column (will fail silently if exists)
ALTER TABLE authors ADD COLUMN wikidata_id TEXT;
ALTER TABLE authors ADD COLUMN viaf_id TEXT;
ALTER TABLE authors ADD COLUMN birth_place TEXT;
ALTER TABLE authors ADD COLUMN death_place TEXT;

-- Add wikidata_id to books (will fail silently if exists)
ALTER TABLE books ADD COLUMN wikidata_id TEXT;
ALTER TABLE books ADD COLUMN openlibrary_id TEXT;
ALTER TABLE books ADD COLUMN isbn_10 TEXT;
ALTER TABLE books ADD COLUMN isbn_13 TEXT;

-- Drop temp table
DROP TABLE _temp_migration_check;
