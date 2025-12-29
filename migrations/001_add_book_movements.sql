-- Migration: Add book_movements table
-- Date: 2025-12-28
-- Description: Adds book-movement relationship table to support literary movement tracking for books

-- Create book-movements join table
CREATE TABLE IF NOT EXISTS book_movements (
    book_id TEXT NOT NULL,
    movement_id TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'wikidata', 'manual', 'llm'
    PRIMARY KEY (book_id, movement_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (movement_id) REFERENCES literary_movements(id) ON DELETE CASCADE
);

-- Create index for common queries
CREATE INDEX IF NOT EXISTS idx_book_movements_book_id ON book_movements(book_id);
CREATE INDEX IF NOT EXISTS idx_book_movements_movement_id ON book_movements(movement_id);
CREATE INDEX IF NOT EXISTS idx_book_movements_source ON book_movements(source);
