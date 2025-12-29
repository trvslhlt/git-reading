-- Migration: Add Phase 2 enrichment features
-- Date: 2025-12-29
-- Description: Adds Phase 2 enrichment tables for existing databases
-- Note: For databases created with schema v3+, these tables already exist
-- This migration consolidates old migrations: 001-003 from /migrations/

-- IMPORTANT: This migration only creates TABLES and INDEXES, which are fully idempotent
-- using IF NOT EXISTS. It does NOT attempt to add columns to existing tables (authors/books)
-- because those additions are not idempotent in SQLite.
--
-- For existing databases that need the enrichment columns (wikidata_id, viaf_id, etc.),
-- those columns should be added manually or were already added via the old migration system.
-- New databases get all columns from the base schema automatically.

-- ============================================================================
-- PART 1: Create book_movements table
-- ============================================================================

CREATE TABLE IF NOT EXISTS book_movements (
    book_id TEXT NOT NULL,
    movement_id TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'wikidata', 'manual', 'llm'
    PRIMARY KEY (book_id, movement_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (movement_id) REFERENCES literary_movements(id) ON DELETE CASCADE
);

-- ============================================================================
-- PART 2: Create awards and book_awards tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS awards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT,  -- 'literary', 'genre-specific', etc.
    established_year INTEGER
);

CREATE TABLE IF NOT EXISTS book_awards (
    book_id TEXT NOT NULL,
    award_id TEXT NOT NULL,
    year_won INTEGER,
    category TEXT,  -- Award category if applicable
    source TEXT NOT NULL,  -- 'wikidata', 'manual', 'llm'
    PRIMARY KEY (book_id, award_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (award_id) REFERENCES awards(id) ON DELETE CASCADE
);

-- ============================================================================
-- PART 3: Create author_influences table
-- ============================================================================

CREATE TABLE IF NOT EXISTS author_influences (
    influencer_id TEXT NOT NULL,
    influenced_id TEXT NOT NULL,
    PRIMARY KEY (influencer_id, influenced_id),
    FOREIGN KEY (influencer_id) REFERENCES authors(id) ON DELETE CASCADE,
    FOREIGN KEY (influenced_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- ============================================================================
-- PART 4: Create indexes (all idempotent with IF NOT EXISTS)
-- ============================================================================

-- Book movements indexes
CREATE INDEX IF NOT EXISTS idx_book_movements_book_id ON book_movements(book_id);
CREATE INDEX IF NOT EXISTS idx_book_movements_movement_id ON book_movements(movement_id);
CREATE INDEX IF NOT EXISTS idx_book_movements_source ON book_movements(source);

-- Book awards indexes
CREATE INDEX IF NOT EXISTS idx_book_awards_book_id ON book_awards(book_id);
CREATE INDEX IF NOT EXISTS idx_book_awards_award_id ON book_awards(award_id);
CREATE INDEX IF NOT EXISTS idx_book_awards_source ON book_awards(source);

-- Author influences indexes
CREATE INDEX IF NOT EXISTS idx_author_influences_influencer ON author_influences(influencer_id);
CREATE INDEX IF NOT EXISTS idx_author_influences_influenced ON author_influences(influenced_id);

-- Wikidata and VIAF indexes (these may fail if columns don't exist, which is fine)
CREATE INDEX IF NOT EXISTS idx_books_wikidata_id ON books(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_books_openlibrary_id ON books(openlibrary_id);
CREATE INDEX IF NOT EXISTS idx_authors_wikidata_id ON authors(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_authors_viaf_id ON authors(viaf_id);
