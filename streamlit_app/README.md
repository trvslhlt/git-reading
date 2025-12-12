# Reading Notes Streamlit App

A multi-page dashboard for visualizing and exploring book reading notes extracted from markdown files.

## Features

### 📊 Analytics Overview
- **Overview Dashboard**: Total books, authors, sections, and items
- **Filtering**: Filter by author and search across all content
- **Book Browser**: Expandable view of each book with all sections
- **Reading Timeline**:
  - Histogram showing reading activity over time
  - Selectable granularity: Year, Quarter, or Month
  - Chronological list of all books with dates
- **Statistics**: Visualizations of books per author and common sections

### 🔍 Semantic Search
- **AI-Powered Search**: Find passages by meaning, not just keywords
- **Smart Filtering**: Filter results by author or section
- **Similarity Scores**: See how relevant each result is
- **Concept Discovery**: Find related ideas even with different wording

### 🗄️ Database Explorer
- **Table Browser**: Browse all database tables with pagination
- **SQL Queries**: Execute custom SQL queries with syntax examples
- **Schema Viewer**: Inspect table structures and relationships
- **Data Export**: Download query results as CSV
- **Quick Stats**: Pre-built insights and visualizations

## Installation

1. Install the optional Streamlit dependencies:
   ```bash
   make streamlit-install
   ```

2. (Optional) For semantic search, install search dependencies:
   ```bash
   make search-install
   ```

## Usage

### First Time Setup

1. **Generate the book index:**
   ```bash
   make run-extract
   ```

2. **Migrate to database** (optional, for Database Explorer):
   ```bash
   make run-migrate
   ```

3. **Build search index** (optional, for Semantic Search):
   ```bash
   make run-search-build
   ```

### Launch the App

```bash
make run-streamlit
```

Or directly:
```bash
streamlit run streamlit_app/app.py
```

Open your browser to `http://localhost:8501`

## Navigation

The app uses **Streamlit's multi-page architecture** with:
- **Main page** (`app.py`): Landing page with setup instructions and status
- **Page 1**: Analytics Overview
- **Page 2**: Semantic Search
- **Page 3**: Database Explorer

Navigate using the sidebar or the buttons on the main page.

## Configuration

- **Index Path**: Configure in the sidebar (default: `INDEX_DIR`)
- **Database Path**: Hardcoded to `DATABASE_PATH`
- **Vector Store**: Hardcoded to `VECTOR_STORE_DIR`

## Updating Data

Whenever you add new reading notes:

```bash
make run-extract                    # Re-extract from markdown
make run-migrate ARGS='--force'     # Update database
make run-search-build               # Rebuild search index
```

Then refresh the Streamlit app to see changes.

## Development

The Streamlit app is intentionally separate from the core `src/` code to keep visualization concerns isolated from the core extraction/validation logic.

### File Structure

```
streamlit_app/
├── app.py                           # Main landing page
└── pages/
    ├── 1_📊_Analytics_Overview.py   # Analytics and stats
    ├── 2_🔍_Semantic_Search.py      # Semantic search interface
    └── 3_🗄️_Database_Explorer.py    # SQL query interface
```

### Adding a New Page

1. Create a new file in `pages/` with format: `N_Icon_Name.py`
2. Add page logic (see existing pages for examples)
3. Streamlit auto-discovers pages in the `pages/` directory

## Troubleshooting

### "No books found"
Run `make run-extract` to generate the index.

### "Search dependencies not installed"
Run `make search-install` to install sentence-transformers and FAISS.

### "Database not found"
Run `make run-migrate` to create the SQLite database.

### "Vector store not found"
Run `make run-search-build` to build the semantic search index.

## Requirements

- Python 3.10+
- Streamlit 1.28.0+
- Pandas 2.0.0+
- (Optional) sentence-transformers, faiss-cpu for semantic search
