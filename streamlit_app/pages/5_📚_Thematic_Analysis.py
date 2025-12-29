"""Thematic Analysis - explore subjects, literary movements, and reading patterns."""

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from load.db import get_adapter  # noqa: E402


@st.cache_data
def load_thematic_data():
    """Load subjects, movements, and their relationships from database.

    Returns:
        dict with subjects, movements, and relationships
    """
    adapter = get_adapter()

    try:
        adapter.connect()

        # Use adapter's database-agnostic string aggregation
        string_agg = adapter.string_agg("bs.source", ",", distinct=True)

        # Get subject distribution
        subjects_query = f"""
            SELECT
                s.id,
                s.name,
                COUNT(DISTINCT bs.book_id) as book_count,
                {string_agg} as sources
            FROM subjects s
            JOIN book_subjects bs ON s.id = bs.subject_id
            GROUP BY s.id, s.name
            ORDER BY book_count DESC
        """
        subjects = adapter.fetchall(subjects_query)

        # Get books with their subjects
        book_subjects_query = """
            SELECT
                b.id as book_id,
                b.title,
                s.name as subject,
                bs.source
            FROM books b
            JOIN book_subjects bs ON b.id = bs.book_id
            JOIN subjects s ON bs.subject_id = s.id
            ORDER BY b.title, s.name
        """
        book_subjects = adapter.fetchall(book_subjects_query)

        # Get literary movements with book counts
        string_agg_movements = adapter.string_agg("bm.source", ",", distinct=True)

        movements_query = f"""
            SELECT
                m.id,
                m.name,
                m.start_year,
                m.end_year,
                COUNT(DISTINCT bm.book_id) as book_count,
                {string_agg_movements} as sources
            FROM literary_movements m
            LEFT JOIN book_movements bm ON m.id = bm.movement_id
            GROUP BY m.id, m.name, m.start_year, m.end_year
            HAVING COUNT(DISTINCT bm.book_id) > 0
            ORDER BY COUNT(DISTINCT bm.book_id) DESC
        """
        movements = adapter.fetchall(movements_query)

        # Get books with their movements
        book_movements_query = """
            SELECT
                b.id as book_id,
                b.title,
                m.name as movement,
                m.start_year,
                m.end_year,
                bm.source
            FROM books b
            JOIN book_movements bm ON b.id = bm.book_id
            JOIN literary_movements m ON bm.movement_id = m.id
            ORDER BY b.title, m.name
        """
        book_movements = adapter.fetchall(book_movements_query)

        # Get authors with their movements
        author_movements_query = """
            SELECT
                a.id as author_id,
                a.name as author_name,
                m.name as movement,
                m.start_year,
                m.end_year,
                am.source
            FROM authors a
            JOIN author_movements am ON a.id = am.author_id
            JOIN literary_movements m ON am.movement_id = m.id
            ORDER BY a.name, m.name
        """
        author_movements = adapter.fetchall(author_movements_query)

        # Get subject co-occurrence
        cooccurrence_query = """
            SELECT
                s1.name as subject1,
                s2.name as subject2,
                COUNT(*) as co_occurrence_count
            FROM book_subjects bs1
            JOIN book_subjects bs2 ON bs1.book_id = bs2.book_id
                AND bs1.subject_id < bs2.subject_id
            JOIN subjects s1 ON bs1.subject_id = s1.id
            JOIN subjects s2 ON bs2.subject_id = s2.id
            GROUP BY bs1.subject_id, bs2.subject_id, s1.name, s2.name
            ORDER BY co_occurrence_count DESC
            LIMIT 50
        """
        subject_cooccurrence = adapter.fetchall(cooccurrence_query)

        # Calculate statistics
        stats = {
            "total_subjects": len(subjects),
            "total_movements": len(movements),
            "books_with_subjects": len({bs["book_id"] for bs in book_subjects}),
            "books_with_movements": len({bm["book_id"] for bm in book_movements}),
            "authors_with_movements": len({am["author_id"] for am in author_movements}),
        }

        return {
            "subjects": subjects,
            "movements": movements,
            "book_subjects": book_subjects,
            "book_movements": book_movements,
            "author_movements": author_movements,
            "subject_cooccurrence": subject_cooccurrence,
            "stats": stats,
        }

    except Exception as e:
        error_msg = str(e)
        if "book_movements" in error_msg.lower() and "does not exist" in error_msg.lower():
            st.error(
                "Database schema is outdated. The `book_movements` table doesn't exist.\n\n"
                "To fix this, recreate your database schema:\n\n"
                "```bash\n"
                "# Back up your data first if needed\n"
                "enrich-db delete  # Warning: deletes all data\n"
                "enrich-db load    # Recreates schema and reloads data\n"
                "```"
            )
        else:
            st.error(f"Error loading thematic data: {e}")
        return {
            "subjects": [],
            "movements": [],
            "book_subjects": [],
            "book_movements": [],
            "author_movements": [],
            "subject_cooccurrence": [],
            "stats": {},
        }
    finally:
        adapter.close()


def main():
    st.title("📚 Thematic Analysis")
    st.markdown("*Explore subjects, literary movements, and reading patterns*")

    # Load thematic data
    with st.spinner("Loading thematic data..."):
        data = load_thematic_data()

    subjects = data["subjects"]
    movements = data["movements"]
    book_subjects = data["book_subjects"]
    book_movements = data["book_movements"]
    author_movements = data["author_movements"]
    subject_cooccurrence = data["subject_cooccurrence"]
    stats = data["stats"]

    if not subjects and not movements:
        st.warning(
            "No subject or movement data found. "
            "Run enrichment first:\n\n"
            "```bash\n"
            "enrich-db enrich --sources openlibrary wikidata\n"
            "```"
        )
        return

    # Overview statistics
    st.header("Overview")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Subjects", stats["total_subjects"])

    with col2:
        st.metric("Total Movements", stats["total_movements"])

    with col3:
        st.metric("Books with Subjects", stats["books_with_subjects"])

    with col4:
        st.metric("Books with Movements", stats["books_with_movements"])

    with col5:
        st.metric("Authors in Movements", stats["authors_with_movements"])

    # Subject Distribution
    if subjects:
        st.header("Subject Distribution")
        st.markdown("*Most common subjects across your reading*")

        # Top subjects chart
        col1, col2 = st.columns([3, 1])

        with col2:
            top_n = st.slider(
                "Number of subjects to show",
                min_value=5,
                max_value=min(50, len(subjects)),
                value=20,
                help="Show top N subjects by book count",
            )

        with col1:
            # Create chart data
            top_subjects = subjects[:top_n]
            subject_data = {s["name"]: s["book_count"] for s in top_subjects}
            st.bar_chart(subject_data)

        # Subject details table
        st.subheader("Subject Details")

        # Source filter
        all_sources = set()
        for s in subjects:
            if s.get("sources"):
                all_sources.update(s["sources"].split(","))

        source_filter = st.multiselect(
            "Filter by source",
            options=sorted(all_sources),
            default=[],
            help="Filter subjects by their data source",
        )

        # Apply filter
        filtered_subjects = subjects
        if source_filter:
            filtered_subjects = [
                s
                for s in subjects
                if s.get("sources") and any(src in s["sources"].split(",") for src in source_filter)
            ]

        # Display table
        subject_table_data = []
        for s in filtered_subjects[:50]:  # Limit to 50 for performance
            subject_table_data.append(
                {
                    "Subject": s["name"],
                    "Books": s["book_count"],
                    "Sources": s.get("sources", ""),
                }
            )

        if subject_table_data:
            df = pd.DataFrame(subject_table_data)
            st.dataframe(df, hide_index=True, width="stretch")
        else:
            st.info("No subjects match the selected filters")

    # Literary Movements
    if movements:
        st.header("Literary Movements")
        st.markdown("*Movements represented in your reading*")

        # Movements table
        movement_table_data = []
        for m in movements:
            period = ""
            if m.get("start_year") and m.get("end_year"):
                period = f"{m['start_year']} - {m['end_year']}"
            elif m.get("start_year"):
                period = f"{m['start_year']} onwards"

            movement_table_data.append(
                {
                    "Movement": m["name"],
                    "Books": m["book_count"],
                    "Period": period,
                    "Sources": m.get("sources", ""),
                }
            )

        if movement_table_data:
            df = pd.DataFrame(movement_table_data)
            st.dataframe(df, hide_index=True, width="stretch")

            # Movement timeline chart (if we have period data)
            movements_with_dates = [
                m for m in movements if m.get("start_year") or m.get("end_year")
            ]
            if movements_with_dates:
                st.subheader("Movement Timeline")
                st.markdown("*Historical periods of literary movements*")

                timeline_data = []
                for m in movements_with_dates[:20]:  # Top 20 for readability
                    start = m.get("start_year") or m.get("end_year", 0)
                    end = m.get("end_year") or start
                    timeline_data.append(
                        {
                            "Movement": m["name"],
                            "Start": start,
                            "End": end,
                            "Books": m["book_count"],
                        }
                    )

                if timeline_data:
                    df = pd.DataFrame(timeline_data)
                    st.dataframe(df, hide_index=True, width="stretch")

    # Subject Co-occurrence
    if subject_cooccurrence:
        st.header("Subject Relationships")
        st.markdown("*Subjects that frequently appear together*")

        st.subheader("Most Common Subject Pairs")

        # Co-occurrence table
        cooccurrence_table_data = []
        for pair in subject_cooccurrence[:20]:  # Top 20 pairs
            cooccurrence_table_data.append(
                {
                    "Subject 1": pair["subject1"],
                    "Subject 2": pair["subject2"],
                    "Books": pair["co_occurrence_count"],
                }
            )

        if cooccurrence_table_data:
            df = pd.DataFrame(cooccurrence_table_data)
            st.dataframe(df, hide_index=True, width="stretch")
        else:
            st.info("No subject co-occurrences found")

    # Books by Subject Explorer
    if book_subjects:
        st.header("Explore Books by Subject")

        # Build subject-to-books mapping
        subject_books = defaultdict(list)
        for bs in book_subjects:
            subject_books[bs["subject"]].append({"title": bs["title"], "source": bs["source"]})

        # Subject selector
        subject_names = sorted(subject_books.keys())
        selected_subject = st.selectbox(
            "Select a subject to see books",
            options=subject_names,
            help="View all books tagged with this subject",
        )

        if selected_subject:
            books = subject_books[selected_subject]
            st.markdown(f"**{len(books)} books** tagged with *{selected_subject}*")

            # Display books
            book_list_data = []
            for book in books:
                book_list_data.append(
                    {
                        "Title": book["title"],
                        "Source": book["source"],
                    }
                )

            df = pd.DataFrame(book_list_data)
            st.dataframe(df, hide_index=True, width="stretch")

    # Books by Movement Explorer
    if book_movements:
        st.header("Explore Books by Movement")

        # Build movement-to-books mapping
        movement_books = defaultdict(list)
        for bm in book_movements:
            movement_books[bm["movement"]].append(
                {
                    "title": bm["title"],
                    "start_year": bm.get("start_year"),
                    "end_year": bm.get("end_year"),
                    "source": bm["source"],
                }
            )

        # Movement selector
        movement_names = sorted(movement_books.keys())
        selected_movement = st.selectbox(
            "Select a movement to see books",
            options=movement_names,
            help="View all books associated with this literary movement",
        )

        if selected_movement:
            books = movement_books[selected_movement]

            # Show movement info
            movement_info = next((m for m in movements if m["name"] == selected_movement), None)
            if movement_info:
                period = ""
                if movement_info.get("start_year") and movement_info.get("end_year"):
                    period = f"{movement_info['start_year']} - {movement_info['end_year']}"
                elif movement_info.get("start_year"):
                    period = f"{movement_info['start_year']} onwards"

                if period:
                    st.markdown(f"**{selected_movement}** ({period})")
                else:
                    st.markdown(f"**{selected_movement}**")

            st.markdown(f"**{len(books)} books** in this movement")

            # Display books
            book_list_data = []
            for book in books:
                book_list_data.append(
                    {
                        "Title": book["title"],
                        "Source": book["source"],
                    }
                )

            df = pd.DataFrame(book_list_data)
            st.dataframe(df, hide_index=True, width="stretch")

    # Authors by Movement
    if author_movements:
        st.header("Authors by Movement")
        st.markdown("*Authors grouped by their literary movements*")

        # Build movement-to-authors mapping
        movement_authors = defaultdict(list)
        for am in author_movements:
            movement_authors[am["movement"]].append(
                {
                    "name": am["author_name"],
                    "start_year": am.get("start_year"),
                    "end_year": am.get("end_year"),
                    "source": am["source"],
                }
            )

        # Movement selector for authors
        movement_names = sorted(movement_authors.keys())
        selected_movement_authors = st.selectbox(
            "Select a movement to see authors",
            options=movement_names,
            help="View all authors associated with this literary movement",
            key="movement_authors_selector",
        )

        if selected_movement_authors:
            authors = movement_authors[selected_movement_authors]

            # Show movement info
            movement_info = next(
                (m for m in movements if m["name"] == selected_movement_authors), None
            )
            if movement_info:
                period = ""
                if movement_info.get("start_year") and movement_info.get("end_year"):
                    period = f"{movement_info['start_year']} - {movement_info['end_year']}"
                elif movement_info.get("start_year"):
                    period = f"{movement_info['start_year']} onwards"

                if period:
                    st.markdown(f"**{selected_movement_authors}** ({period})")
                else:
                    st.markdown(f"**{selected_movement_authors}**")

            st.markdown(f"**{len(authors)} authors** in this movement")

            # Display authors
            author_list_data = []
            for author in authors:
                author_list_data.append({"Author": author["name"], "Source": author["source"]})

            df = pd.DataFrame(author_list_data)
            st.dataframe(df, hide_index=True, width="stretch")


if __name__ == "__main__":
    main()
