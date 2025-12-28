-- Migration: Add author_influences table
-- Date: 2025-12-28
-- Description: Adds author_influences table to track bidirectional influence relationships

-- Create author_influences table
CREATE TABLE IF NOT EXISTS author_influences (
    influencer_id TEXT NOT NULL,
    influenced_id TEXT NOT NULL,
    PRIMARY KEY (influencer_id, influenced_id),
    FOREIGN KEY (influencer_id) REFERENCES authors(id) ON DELETE CASCADE,
    FOREIGN KEY (influenced_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_author_influences_influencer ON author_influences(influencer_id);
CREATE INDEX IF NOT EXISTS idx_author_influences_influenced ON author_influences(influenced_id);
