"""Semantic search page - search reading notes using vector similarity."""

from pathlib import Path

import streamlit as st


def main():
    st.title("🔍 Semantic Search")
    st.markdown("*Find similar passages using AI-powered semantic search*")

    # Check if vector store exists
    vector_store_path = Path("./data/vector_store")
    if not vector_store_path.exists():
        st.warning(
            "Vector store not found. Build the search index first:\n\n"
            "```bash\nsearch build --index-dir <path> --output <path>\n```"
        )
        st.info(
            "💡 **What is semantic search?**\n\n"
            "Semantic search finds passages based on _meaning_ rather than exact keyword matches. "
            "It uses AI to understand that 'happiness' is related to 'joy' and 'contentment', "
            "even if those exact words don't appear in your query."
        )
        return

    # Try to import search dependencies
    try:
        from query.search import search_notes
        from query.vector_store import VectorStore
    except ImportError as e:
        st.error(
            f"Search dependencies not installed: {e}\n\n"
            "Install with:\n```bash\nmake search-install\n```"
        )
        return

    # Load vector store
    @st.cache_resource
    def load_vector_store():
        """Load the vector store (cached)."""
        return VectorStore.load(vector_store_path)

    try:
        with st.spinner("Loading search index..."):
            store = load_vector_store()
            stats = store.get_stats()
    except Exception as e:
        st.error(f"Failed to load vector store: {e}")
        return

    # Show index stats
    with st.expander("📊 Search Index Stats", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Notes", stats["total_notes"])
        with col2:
            st.metric("Authors", stats["unique_authors"])
        with col3:
            st.metric("Books", stats["unique_books"])
        with col4:
            st.metric("Sections", stats["unique_sections"])

    # Search interface
    st.header("Search")

    query = st.text_input(
        "Enter your search query",
        placeholder="e.g., the meaning of life, overcoming adversity, nature and beauty",
        help="Describe what you're looking for in natural language",
    )

    # Search options
    col1, col2, col3 = st.columns(3)

    with col1:
        top_k = st.slider(
            "Number of results",
            min_value=1,
            max_value=20,
            value=5,
            help="How many similar passages to return",
        )

    with col2:
        filter_author = st.selectbox(
            "Filter by author",
            options=["All Authors"] + sorted(stats.get("authors", [])),
            help="Only search within this author's works",
        )

    with col3:
        filter_section = st.selectbox(
            "Filter by section",
            options=["All Sections"] + sorted(stats.get("sections", [])),
            help="Only search within this section type",
        )

    # Convert "All" selections to None
    filter_author = None if filter_author == "All Authors" else filter_author
    filter_section = None if filter_section == "All Sections" else filter_section

    # Search button
    if st.button("🔍 Search", type="primary", use_container_width=True) or query:
        if not query:
            st.warning("Please enter a search query")
            return

        with st.spinner("Searching..."):
            try:
                results = search_notes(
                    query=query,
                    vector_store_dir=vector_store_path,
                    k=top_k,
                    filter_author=filter_author,
                    filter_section=filter_section,
                )

                if not results:
                    st.info("No results found. Try a different query or remove filters.")
                    return

                # Display results
                st.header(f"Results ({len(results)})")

                for i, result in enumerate(results, 1):
                    similarity_pct = result["similarity"] * 100

                    # Color code by similarity
                    if similarity_pct >= 80:
                        color = "green"
                    elif similarity_pct >= 60:
                        color = "orange"
                    else:
                        color = "red"

                    with st.container():
                        col1, col2 = st.columns([4, 1])

                        with col1:
                            st.markdown(f"### {i}. {result['book_title']}")
                            st.markdown(
                                f"**by {result['author']}** • Section: `{result['section']}`"
                            )

                        with col2:
                            st.markdown(
                                f"<div style='text-align: right; color: {color}; font-size: 24px; font-weight: bold;'>"
                                f"{similarity_pct:.1f}%</div>",
                                unsafe_allow_html=True,
                            )

                        # Display the text
                        st.markdown("---")
                        st.markdown(result["text"])

                        # Show date if available
                        if result.get("date_read"):
                            st.caption(f"📅 Read on: {result['date_read']}")

                        st.markdown("")  # Spacing

            except Exception as e:
                st.error(f"Search failed: {e}")
                st.exception(e)

    # Help section
    with st.expander("💡 Search Tips"):
        st.markdown(
            """
        **How to use semantic search:**

        1. **Use natural language** - Describe what you're looking for as you would to a friend
           - Good: "dealing with loss and grief"
           - Also good: "finding meaning in difficult times"

        2. **Filters are powerful** - Use author or section filters to narrow your search
           - Search only in "excerpts" for direct quotes
           - Search only in "notes" for your own thoughts

        3. **Similarity scores** - Higher is better
           - 🟢 **80%+**: Very relevant matches
           - 🟠 **60-80%**: Somewhat related
           - 🔴 **<60%**: Loosely connected

        4. **Try variations** - If you don't find what you want, rephrase your query
           - Instead of "happiness", try "joy", "contentment", or "well-being"

        5. **No exact matches needed** - The search understands concepts, not just keywords
        """
        )


if __name__ == "__main__":
    main()
