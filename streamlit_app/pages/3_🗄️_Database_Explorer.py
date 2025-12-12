"""Database explorer page - browse and query the SQLite database."""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


def get_table_names(conn: sqlite3.Connection) -> list[str]:
    """Get list of tables in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> list[tuple]:
    """Get schema information for a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return cursor.fetchall()


def get_table_count(conn: sqlite3.Connection, table_name: str) -> int:
    """Get row count for a table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def execute_query(conn: sqlite3.Connection, query: str) -> tuple[list, list]:
    """Execute a SQL query and return results."""
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    return columns, results


def main():
    st.title("🗄️ Database Explorer")
    st.markdown("*Browse and query the SQLite reading notes database*")

    # Check if database exists
    db_path = Path("./data/readings.db")
    if not db_path.exists():
        st.warning(
            "Database not found. Run the migration first:\n\n"
            "```bash\nload-db migrate --index-dir <path> --database <path>\n```"
        )
        st.info(
            "💡 **What is the database?**\n\n"
            "The SQLite database stores all your reading notes in a structured format "
            "that's easier to query and extend than a single JSON file. "
            "It includes tables for books, authors, excerpts, and their relationships."
        )
        return

    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return

    # Get list of tables
    tables = get_table_names(conn)

    if not tables:
        st.warning("No tables found in database")
        conn.close()
        return

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Table Browser", "🔍 SQL Query", "📋 Quick Stats"])

    with tab1:
        st.header("Table Browser")

        # Table selector
        selected_table = st.selectbox(
            "Select a table",
            options=tables,
            help="Choose a table to browse",
        )

        if selected_table:
            # Show schema
            with st.expander("📐 Table Schema", expanded=False):
                schema = get_table_schema(conn, selected_table)
                schema_df = pd.DataFrame(
                    schema,
                    columns=["Column ID", "Name", "Type", "NotNull", "Default", "PrimaryKey"],
                )
                st.dataframe(schema_df, use_container_width=True, hide_index=True)

            # Get row count
            row_count = get_table_count(conn, selected_table)
            st.metric("Total Rows", row_count)

            # Pagination controls
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                rows_per_page = st.select_slider(
                    "Rows per page",
                    options=[10, 25, 50, 100, 500],
                    value=25,
                )

            with col2:
                max_pages = max(1, (row_count + rows_per_page - 1) // rows_per_page)
                page = st.number_input(
                    "Page",
                    min_value=1,
                    max_value=max_pages,
                    value=1,
                )

            with col3:
                st.markdown(f"**of {max_pages}**")

            # Calculate offset
            offset = (page - 1) * rows_per_page

            # Query data with pagination
            query = f"SELECT * FROM {selected_table} LIMIT {rows_per_page} OFFSET {offset}"

            try:
                columns, results = execute_query(conn, query)

                if results:
                    # Convert to DataFrame for nice display
                    df = pd.DataFrame(results, columns=columns)
                    st.dataframe(df, use_container_width=True, height=400)

                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{selected_table}_page{page}.csv",
                        mime="text/csv",
                    )
                else:
                    st.info(f"No rows found in {selected_table}")

            except Exception as e:
                st.error(f"Query failed: {e}")

    with tab2:
        st.header("SQL Query")

        st.markdown(
            "**Execute custom SQL queries**\n\n"
            "Write your own SQL to explore the data. "
            "Be careful with UPDATE/DELETE queries - this is a live database!"
        )

        # Query examples
        with st.expander("📝 Example Queries"):
            st.code(
                """
-- Get all books by an author
SELECT b.title, b.publication_year
FROM books b
JOIN book_authors ba ON b.id = ba.book_id
JOIN authors a ON ba.author_id = a.id
WHERE a.name = 'Philip Roth';

-- Count excerpts per section
SELECT section, COUNT(*) as count
FROM chunks
GROUP BY section
ORDER BY count DESC;

-- Top 10 most excerpted books
SELECT b.title, a.name, COUNT(*) as excerpt_count
FROM chunks c
JOIN books b ON c.book_id = b.id
JOIN book_authors ba ON b.id = ba.book_id
JOIN authors a ON ba.author_id = a.id
WHERE c.section = 'excerpts'
GROUP BY b.id, b.title, a.name
ORDER BY excerpt_count DESC
LIMIT 10;

-- Find books with notes containing specific words
SELECT DISTINCT b.title, a.name
FROM chunks c
JOIN books b ON c.book_id = b.id
JOIN book_authors ba ON b.id = ba.book_id
JOIN authors a ON ba.author_id = a.id
WHERE c.section = 'notes'
AND c.excerpt LIKE '%meaning%';
""",
                language="sql",
            )

        # SQL input
        default_query = f"SELECT * FROM {tables[0]} LIMIT 10"
        sql_query = st.text_area(
            "Enter SQL query",
            value=default_query,
            height=150,
            help="Write your SQL query here. Results will be shown below.",
        )

        # Read-only mode toggle
        read_only = st.checkbox(
            "🔒 Read-only mode (blocks UPDATE/DELETE/INSERT)",
            value=True,
            help="Recommended to prevent accidental data modification",
        )

        if st.button("▶️ Execute Query", type="primary"):
            # Check for dangerous operations in read-only mode
            if read_only:
                dangerous_keywords = ["UPDATE", "DELETE", "INSERT", "DROP", "ALTER", "CREATE"]
                query_upper = sql_query.upper()
                if any(keyword in query_upper for keyword in dangerous_keywords):
                    st.error(
                        "Query blocked: Modifying operations not allowed in read-only mode. "
                        "Uncheck read-only mode to execute."
                    )
                    return

            try:
                with st.spinner("Executing query..."):
                    columns, results = execute_query(conn, sql_query)

                    if results:
                        st.success(f"Query returned {len(results)} rows")

                        # Display results
                        df = pd.DataFrame(results, columns=columns)
                        st.dataframe(df, use_container_width=True, height=400)

                        # Download results
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download results as CSV",
                            data=csv,
                            file_name="query_results.csv",
                            mime="text/csv",
                        )
                    else:
                        st.info("Query executed successfully (no results returned)")

            except Exception as e:
                st.error(f"Query failed: {e}")
                st.exception(e)

    with tab3:
        st.header("Quick Stats")

        # Database overview
        st.subheader("Database Overview")

        stats_data = []
        for table in tables:
            count = get_table_count(conn, table)
            stats_data.append({"Table": table, "Rows": count})

        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        # Quick insights
        st.subheader("Quick Insights")

        col1, col2 = st.columns(2)

        with col1:
            # Top authors by book count
            st.markdown("**Top 10 Authors by Book Count**")
            try:
                query = """
                    SELECT a.name, COUNT(DISTINCT ba.book_id) as book_count
                    FROM authors a
                    JOIN book_authors ba ON a.id = ba.author_id
                    GROUP BY a.id, a.name
                    ORDER BY book_count DESC
                    LIMIT 10
                """
                columns, results = execute_query(conn, query)
                df = pd.DataFrame(results, columns=columns)
                st.bar_chart(df.set_index("name"))
            except Exception as e:
                st.error(f"Failed to load author stats: {e}")

        with col2:
            # Section distribution
            st.markdown("**Section Distribution**")
            try:
                query = """
                    SELECT section, COUNT(*) as count
                    FROM chunks
                    GROUP BY section
                    ORDER BY count DESC
                """
                columns, results = execute_query(conn, query)
                df = pd.DataFrame(results, columns=columns)
                st.bar_chart(df.set_index("section"))
            except Exception as e:
                st.error(f"Failed to load section stats: {e}")

        # Most excerpted books
        st.subheader("Top 10 Most Excerpted Books")
        try:
            query = """
                SELECT b.title, a.name as author, COUNT(*) as excerpt_count
                FROM chunks c
                JOIN books b ON c.book_id = b.id
                JOIN book_authors ba ON b.id = ba.book_id
                JOIN authors a ON ba.author_id = a.id
                WHERE c.section = 'excerpts'
                GROUP BY b.id, b.title, a.name
                ORDER BY excerpt_count DESC
                LIMIT 10
            """
            columns, results = execute_query(conn, query)
            df = pd.DataFrame(results, columns=columns)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Failed to load top books: {e}")

    # Close connection
    conn.close()


if __name__ == "__main__":
    main()
