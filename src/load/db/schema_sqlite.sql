-- SQLite schema for git-reading metadata storage
-- This schema stores book metadata, author information, and note references
-- that complement the FAISS vector store.

-- Books table
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,

    -- ISBN identifiers
    isbn TEXT,
    isbn_10 TEXT,
    isbn_13 TEXT,

    -- Publication metadata
    publication_year INTEGER,
    publisher TEXT,
    page_count INTEGER,
    language TEXT,
    description TEXT,
    cover_url TEXT,

    -- External IDs for cross-referencing
    openlibrary_id TEXT,
    wikidata_id TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL UNIQUE,

    -- Biographical data
    birth_year INTEGER,
    death_year INTEGER,
    birth_place TEXT,
    death_place TEXT,
    nationality TEXT,
    bio TEXT,

    -- External IDs
    wikidata_id TEXT,
    wikipedia_url TEXT,
    viaf_id TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Book-Author relationship (many-to-many)
CREATE TABLE IF NOT EXISTS book_authors (
    book_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_role TEXT DEFAULT 'author',
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Subjects table (formerly genres) - normalized hierarchical taxonomy
CREATE TABLE IF NOT EXISTS subjects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    parent_id TEXT,
    subject_type TEXT,  -- 'genre', 'topic', 'period', 'movement', etc.
    FOREIGN KEY (parent_id) REFERENCES subjects(id)
);

-- Book-Subject relationship with source tracking
CREATE TABLE IF NOT EXISTS book_subjects (
    book_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'openlibrary', 'wikidata', 'manual', 'llm'
    confidence REAL,  -- 0.0-1.0 for LLM-generated classifications
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (book_id, subject_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Literary movements table
CREATE TABLE IF NOT EXISTS literary_movements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    start_year INTEGER,
    end_year INTEGER,
    description TEXT
);

-- Author-Movement relationship
CREATE TABLE IF NOT EXISTS author_movements (
    author_id TEXT NOT NULL,
    movement_id TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'wikidata', 'manual', 'llm'
    PRIMARY KEY (author_id, movement_id),
    FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE,
    FOREIGN KEY (movement_id) REFERENCES literary_movements(id) ON DELETE CASCADE
);

-- Notes table - references to excerpts with their vector positions
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT UNIQUE,
    book_id TEXT NOT NULL,
    section TEXT,
    excerpt TEXT NOT NULL,
    page_number INTEGER,
    faiss_index INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Metadata table for tracking extraction checkpoints
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Author influences (for graph exploration)
CREATE TABLE IF NOT EXISTS author_influences (
    influencer_id TEXT NOT NULL,
    influenced_id TEXT NOT NULL,
    relationship_type TEXT DEFAULT 'influenced',
    PRIMARY KEY (influencer_id, influenced_id),
    FOREIGN KEY (influencer_id) REFERENCES authors(id) ON DELETE CASCADE,
    FOREIGN KEY (influenced_id) REFERENCES authors(id) ON DELETE CASCADE
);

-- Enrichment metadata table - tracks when/how each field was enriched
CREATE TABLE IF NOT EXISTS enrichment_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,  -- 'book', 'author'
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    source TEXT NOT NULL,  -- 'openlibrary', 'wikidata', 'google_books', 'manual', 'llm'
    method TEXT NOT NULL,  -- 'api', 'manual_entry', 'llm_generated'
    api_endpoint TEXT,  -- specific API endpoint used
    confidence REAL,  -- For LLM-generated data
    enriched_by TEXT,  -- user identifier for manual entries
    enriched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT  -- additional context
);

-- Manual tags/corrections table
CREATE TABLE IF NOT EXISTS manual_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    tag_type TEXT NOT NULL,  -- 'subject', 'correction', 'note'
    tag_value TEXT NOT NULL,
    added_by TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_notes_book_id ON notes(book_id);
CREATE INDEX IF NOT EXISTS idx_notes_faiss_index ON notes(faiss_index);
CREATE INDEX IF NOT EXISTS idx_notes_item_id ON notes(item_id);
CREATE INDEX IF NOT EXISTS idx_book_authors_book_id ON book_authors(book_id);
CREATE INDEX IF NOT EXISTS idx_book_authors_author_id ON book_authors(author_id);
CREATE INDEX IF NOT EXISTS idx_book_subjects_book_id ON book_subjects(book_id);
CREATE INDEX IF NOT EXISTS idx_book_subjects_subject_id ON book_subjects(subject_id);
CREATE INDEX IF NOT EXISTS idx_book_subjects_source ON book_subjects(source);
CREATE INDEX IF NOT EXISTS idx_authors_name_parts ON authors(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_books_openlibrary_id ON books(openlibrary_id);
CREATE INDEX IF NOT EXISTS idx_books_wikidata_id ON books(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_books_isbn_13 ON books(isbn_13);
CREATE INDEX IF NOT EXISTS idx_authors_wikidata_id ON authors(wikidata_id);
CREATE INDEX IF NOT EXISTS idx_authors_viaf_id ON authors(viaf_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_log_entity ON enrichment_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_log_source ON enrichment_log(source);
CREATE INDEX IF NOT EXISTS idx_enrichment_log_field ON enrichment_log(field_name);
CREATE INDEX IF NOT EXISTS idx_manual_tags_entity ON manual_tags(entity_type, entity_id);
