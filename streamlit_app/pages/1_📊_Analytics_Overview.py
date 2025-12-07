"""Analytics overview page - statistics and visualizations of reading notes."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


def load_index(index_path: Path) -> dict:
    """Load the book index JSON file."""
    if not index_path.exists():
        return {"books": [], "total_books": 0}
    with open(index_path) as f:
        return json.load(f)


def main():
    st.title("📊 Analytics Overview")
    st.markdown("*Statistics and visualizations of your reading notes*")

    # Get index path from session state (set in main app)
    index_path = st.session_state.get("index_path", ".tmp/index.json")

    # Load data
    data = load_index(Path(index_path))
    books = data.get("books", [])
    total_books = data.get("total_books", 0)

    if total_books == 0:
        st.warning(
            f"No books found in `{index_path}`. Run the extract command first:\n\n"
            "```bash\nmake run-extract\n```"
        )
        return

    # Overview metrics
    st.header("Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Books", total_books)

    with col2:
        authors = {book["author"] for book in books}
        st.metric("Authors", len(authors))

    with col3:
        total_sections = sum(len(book.get("sections", {})) for book in books)
        st.metric("Total Sections", total_sections)

    with col4:
        total_items = sum(
            sum(len(items) for items in book.get("sections", {}).values()) for book in books
        )
        st.metric("Total Items", total_items)

    # Filters
    st.header("Filters")
    col1, col2 = st.columns(2)

    with col1:
        selected_authors = st.multiselect(
            "Filter by Author",
            options=sorted(authors),
            default=[],
            help="Leave empty to show all authors",
        )

    with col2:
        search_query = st.text_input(
            "Search in titles, notes, excerpts",
            help="Search across book titles and content",
        )

    # Apply filters
    filtered_books = books
    if selected_authors:
        filtered_books = [b for b in filtered_books if b["author"] in selected_authors]

    if search_query:
        query_lower = search_query.lower()
        filtered_books = [
            b
            for b in filtered_books
            if query_lower in b["title"].lower()
            or any(
                query_lower in item.lower()
                for section_items in b.get("sections", {}).values()
                for item in section_items
            )
        ]

    st.markdown(f"**Showing {len(filtered_books)} of {total_books} books**")

    # Display books
    st.header("Books")

    for book in filtered_books:
        with st.expander(f"**{book['title']}** by {book['author']}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Author:** {book['author']}")
                if book.get("date_read"):
                    st.markdown(f"**Date Read:** {book['date_read']}")
                st.markdown(f"**Source:** `{book.get('source_file', 'Unknown')}`")

            with col2:
                sections = book.get("sections", {})
                st.markdown("**Sections:**")
                for section_name in sections.keys():
                    item_count = len(sections[section_name])
                    st.markdown(f"- {section_name}: {item_count} items")

            # Display sections
            sections = book.get("sections", {})
            if sections:
                st.markdown("---")
                tabs = st.tabs(list(sections.keys()))

                for tab, (section_name, items) in zip(tabs, sections.items(), strict=True):
                    with tab:
                        if items:
                            for idx, item in enumerate(items, 1):
                                st.markdown(f"{idx}. {item}")
                        else:
                            st.info(f"No items in {section_name}")

    # Reading timeline
    if books:
        st.header("Reading Timeline")

        # Parse dates and create timeline data
        dated_books = [
            (book, datetime.fromisoformat(book["date_read"]))
            for book in books
            if book.get("date_read")
        ]

        if dated_books:
            dated_books.sort(key=lambda x: x[1])

            # Time period histogram
            st.subheader("Reading Activity Over Time")

            col1, col2 = st.columns([3, 1])

            with col2:
                granularity = st.selectbox(
                    "Group by",
                    ["Year", "Quarter", "Month"],
                    help="Choose time period granularity",
                )

            # Group books by selected time period
            period_counts = {}
            for _book, date in dated_books:
                if granularity == "Year":
                    period_key = date.strftime("%Y")
                elif granularity == "Quarter":
                    quarter = (date.month - 1) // 3 + 1
                    period_key = f"{date.year} Q{quarter}"
                else:  # Month
                    period_key = date.strftime("%Y-%m")

                period_counts[period_key] = period_counts.get(period_key, 0) + 1

            # Create histogram
            if period_counts:
                df = pd.DataFrame(list(period_counts.items()), columns=["Period", "Books Read"])
                df = df.sort_values("Period")

                with col1:
                    st.bar_chart(df.set_index("Period"), height=300)

                # Show summary stats
                st.markdown(
                    f"**Total periods with reading activity:** {len(period_counts)} | "
                    f"**Average per period:** {sum(period_counts.values()) / len(period_counts):.1f} books"
                )

            # Detailed timeline table
            st.subheader("Chronological List")
            timeline_data = []
            for book, date in dated_books:
                timeline_data.append(
                    {
                        "Date": date.strftime("%Y-%m-%d"),
                        "Book": book["title"],
                        "Author": book["author"],
                    }
                )

            st.dataframe(
                timeline_data,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No date information available for timeline visualization")

    # Statistics
    st.header("Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Books per Author")
        author_counts = {}
        for book in books:
            author = book["author"]
            author_counts[author] = author_counts.get(author, 0) + 1

        st.bar_chart(author_counts)

    with col2:
        st.subheader("Most Common Sections")
        section_counts = {}
        for book in books:
            for section_name in book.get("sections", {}).keys():
                section_counts[section_name] = section_counts.get(section_name, 0) + 1

        st.bar_chart(section_counts)


if __name__ == "__main__":
    main()
