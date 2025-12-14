"""Streamlit app for visualizing and exploring book reading notes.

This is a multi-page app with:
1. Analytics Overview - Statistics and visualizations
2. Semantic Search - AI-powered search of your notes
3. Database Explorer - Browse and query the database (PostgreSQL or SQLite)

Run with: streamlit run streamlit_app/app.py
"""

import streamlit as st

from common.constants import INDEX_DIR, VECTOR_STORE_DIR
from common.env import env

# Page configuration
st.set_page_config(
    page_title="Reading Notes Explorer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "index_dir" not in st.session_state:
    st.session_state.index_dir = str(INDEX_DIR)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Index directory setting
    index_dir = st.text_input(
        "Extraction Files Directory",
        value=st.session_state.index_dir,
        help="Path to the directory containing extraction files",
        key="index_dir_input",
    )

    # Update session state
    if index_dir != st.session_state.index_dir:
        st.session_state.index_dir = index_dir

    st.markdown("---")

    # Quick links
    st.markdown("**📚 Pages**")
    st.page_link("pages/1_📊_Analytics_Overview.py", label="Analytics Overview", icon="📊")
    st.page_link("pages/2_🔍_Semantic_Search.py", label="Semantic Search", icon="🔍")
    st.page_link("pages/3_🗄️_Database_Explorer.py", label="Database Explorer", icon="🗄️")

    st.markdown("---")

    # About section
    st.markdown("**ℹ️ About**")
    st.markdown(
        "This app provides multiple ways to explore your reading notes:\n\n"
        "- **Analytics**: View statistics and trends\n"
        "- **Search**: Find passages by meaning\n"
        "- **Database**: Query with SQL"
    )

# Main page content
st.title("📚 Reading Notes Explorer")
st.markdown("*Multi-tool dashboard for your reading notes*")

st.markdown("---")

# Welcome section
st.header("Welcome!")

st.markdown(
    """
This app helps you explore and analyze your reading notes in multiple ways.
Choose a page from the sidebar to get started:
"""
)

# Page descriptions
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📊 Analytics Overview")
    st.markdown(
        """
View comprehensive statistics about your reading:
- Total books, authors, and notes
- Reading timeline and trends
- Author and section breakdowns
- Search and filter by content

Perfect for understanding your reading patterns.
"""
    )
    if st.button("Go to Analytics →", width="stretch"):
        st.switch_page("pages/1_📊_Analytics_Overview.py")

with col2:
    st.subheader("🔍 Semantic Search")
    st.markdown(
        """
Find passages using AI-powered search:
- Search by meaning, not keywords
- Filter by author or section
- See similarity scores
- Discover related concepts

Perfect for finding that quote you remember.
"""
    )
    if st.button("Go to Search →", width="stretch"):
        st.switch_page("pages/2_🔍_Semantic_Search.py")

with col3:
    st.subheader("🗄️ Database Explorer")
    db_type = env.database_type()
    st.markdown(
        f"""
Query the {db_type.upper()} database directly:
- Browse all tables
- Execute custom SQL queries
- View schema and relationships
- Export data to CSV

Perfect for advanced analysis and exports.
"""
    )
    if st.button("Go to Database →", width="stretch"):
        st.switch_page("pages/3_🗄️_Database_Explorer.py")

st.markdown("---")

# Quick setup guide
with st.expander("🚀 Quick Setup Guide", expanded=False):
    db_type = env.database_type()
    if db_type.lower() == "postgresql":
        db_setup = """
2. **Configure database** (PostgreSQL - default)
   ```bash
   make postgres-up           # Start PostgreSQL
   cp .env.example .env       # Configure credentials
   ```
   Edit `.env` to set DATABASE_TYPE=postgresql and connection details.
"""
    else:
        db_setup = """
2. **Configure database** (SQLite)
   ```bash
   cp .env.example .env       # Configure credentials
   ```
   Edit `.env` to set DATABASE_TYPE=sqlite and DATABASE_PATH.
"""

    st.markdown(
        f"""
### First Time Setup

1. **Extract your reading notes**
   ```bash
   extract readings --notes-dir <path>
   ```
   This creates extraction files in `./data/index/` from your markdown files.
{db_setup}
3. **Load to database** (optional, for Database Explorer)
   ```bash
   load-db load --index-dir data/index
   ```
   Database configuration is read from `.env` file.

4. **Build search index** (optional, for Semantic Search)
   ```bash
   search build --index-dir data/index --output data/vector_store
   ```
   This creates a vector store for semantic search.

### Updating Data

Whenever you add new reading notes:

```bash
extract readings --notes-dir <path>              # Re-extract (incremental)
load-db load --index-dir data/index --incremental  # Update database
search build --index-dir data/index --output data/vector_store --incremental # Update search
```

Then refresh this app to see the changes!
"""
    )

# Status indicators
st.markdown("---")
st.subheader("📋 Data Status")

col1, col2, col3 = st.columns(3)

with col1:
    from pathlib import Path

    index_exists = Path(st.session_state.index_dir).exists()
    if index_exists:
        st.success("✅ Extraction files found")
    else:
        st.error("❌ Extraction files not found")
        st.caption("Run `extract readings --notes-dir <path>`")

with col2:
    from load.db import get_adapter

    db_type = env.database_type()

    # Database status check - use adapter interface
    try:
        adapter = get_adapter()  # Uses env config
        db_exists = adapter.exists()
        db_label = f"Database ({db_type})"
    except Exception:
        db_exists = False
        db_label = f"Database ({db_type})"

    if db_exists:
        st.success(f"✅ {db_label} found")
    else:
        st.warning(f"⚠️ {db_label} not found")
        st.caption("Run `load-db load --index-dir data/index`")

with col3:
    vector_exists = Path(VECTOR_STORE_DIR).exists()
    if vector_exists:
        st.success("✅ Search index found")
    else:
        st.warning("⚠️ Search index not found")
        st.caption("Run `search build --index-dir <path> --output <path>`")
