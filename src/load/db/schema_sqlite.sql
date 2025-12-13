-- SQLite schema for git-reading metadata storage
-- This schema stores book metadata, author information, and note references
-- that complement the FAISS vector store.

-- Books table
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    isbn TEXT,
    publication_year INTEGER,
    publisher TEXT,
    page_count INTEGER,
    language TEXT,
    description TEXT,
    cover_url TEXT,
    goodreads_rating REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Authors table
CREATE TABLE IF NOT EXISTS authors (
    id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL UNIQUE,
    birth_year INTEGER,
    death_year INTEGER,
    nationality TEXT,
    bio TEXT,
    wikipedia_url TEXT,
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

-- Genres/subjects table
CREATE TABLE IF NOT EXISTS genres (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    parent_id TEXT,
    FOREIGN KEY (parent_id) REFERENCES genres(id)
);

-- Book-Genre relationship (many-to-many)
CREATE TABLE IF NOT EXISTS book_genres (
    book_id TEXT NOT NULL,
    genre_id TEXT NOT NULL,
    PRIMARY KEY (book_id, genre_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_notes_book_id ON notes(book_id);
CREATE INDEX IF NOT EXISTS idx_notes_faiss_index ON notes(faiss_index);
CREATE INDEX IF NOT EXISTS idx_notes_item_id ON notes(item_id);
CREATE INDEX IF NOT EXISTS idx_book_authors_book_id ON book_authors(book_id);
CREATE INDEX IF NOT EXISTS idx_book_authors_author_id ON book_authors(author_id);
CREATE INDEX IF NOT EXISTS idx_book_genres_book_id ON book_genres(book_id);
CREATE INDEX IF NOT EXISTS idx_book_genres_genre_id ON book_genres(genre_id);
CREATE INDEX IF NOT EXISTS idx_authors_name_parts ON authors(first_name, last_name);
