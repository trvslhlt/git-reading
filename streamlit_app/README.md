# Reading Notes Streamlit App

This is a development/preview tool for visualizing book reading notes extracted from markdown files.

## Features

- **Overview Dashboard**: Total books, authors, sections, and items
- **Filtering**: Filter by author and search across all content
- **Book Browser**: Expandable view of each book with all sections
- **Reading Timeline**:
  - Histogram showing reading activity over time
  - Selectable granularity: Year, Quarter, or Month
  - Chronological list of all books with dates
- **Statistics**: Visualizations of books per author and common sections

## Installation

Install the optional Streamlit dependencies:

```bash
uv pip install -e ".[streamlit]"
```

## Usage

1. First, generate the book index:
   ```bash
   make run-extract
   ```

2. Run the Streamlit app:
   ```bash
   make run-streamlit
   ```

   Or directly:
   ```bash
   streamlit run streamlit_app/app.py
   ```

3. Open your browser to `http://localhost:8501`

## Configuration

By default, the app looks for `index.json` in the current directory. You can configure the path in the sidebar.

## Development

The Streamlit app is intentionally separate from the core `src/` code to keep visualization concerns isolated from the core extraction/validation logic.
