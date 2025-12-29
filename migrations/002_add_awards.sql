-- Migration: Add awards and book_awards tables
-- Date: 2025-12-28
-- Description: Adds awards table and book-award relationship table to support award tracking

-- Create awards table
CREATE TABLE IF NOT EXISTS awards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT,  -- 'literary', 'genre-specific', etc.
    established_year INTEGER
);

-- Create book-awards join table
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

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_book_awards_book_id ON book_awards(book_id);
CREATE INDEX IF NOT EXISTS idx_book_awards_award_id ON book_awards(award_id);
CREATE INDEX IF NOT EXISTS idx_book_awards_source ON book_awards(source);
