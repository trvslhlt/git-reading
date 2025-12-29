"""Reading Statistics - temporal patterns, demographics, and publication analysis."""

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from load.db import get_adapter  # noqa: E402


@st.cache_data
def load_reading_stats():
    """Load reading statistics from database.

    Returns:
        dict with books, authors, and statistics
    """
    adapter = get_adapter()

    try:
        adapter.connect()

        # Get all books with metadata
        # Note: Books can have multiple authors, but for stats we'll take the first one
        books_query = """
            SELECT DISTINCT ON (b.id)
                b.id,
                b.title,
                b.publication_year,
                b.date_read,
                b.isbn_13,
                a.name as author_name,
                a.first_name,
                a.last_name,
                a.nationality,
                a.birth_year,
                a.death_year
            FROM books b
            LEFT JOIN book_authors ba ON b.id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.id
            ORDER BY b.id, ba.author_id
        """
        books = adapter.fetchall(books_query)

        # Get authors with enrichment data
        authors_query = """
            SELECT
                id,
                name,
                nationality,
                birth_year,
                death_year,
                wikidata_id
            FROM authors
            ORDER BY name
        """
        authors = adapter.fetchall(authors_query)

        # Get award-winning books
        awards_query = """
            SELECT
                b.id as book_id,
                b.title,
                a.name as award_name,
                ba.year_won
            FROM books b
            JOIN book_awards ba ON b.id = ba.book_id
            JOIN awards a ON ba.award_id = a.id
            ORDER BY b.title, a.name
        """
        book_awards = adapter.fetchall(awards_query)

        # Get books per author count
        books_per_author_query = """
            SELECT
                a.name,
                COUNT(DISTINCT ba.book_id) as book_count
            FROM authors a
            LEFT JOIN book_authors ba ON a.id = ba.author_id
            GROUP BY a.id, a.name
            HAVING COUNT(DISTINCT ba.book_id) > 0
            ORDER BY COUNT(DISTINCT ba.book_id) DESC, a.name
        """
        books_per_author = adapter.fetchall(books_per_author_query)

        # Calculate statistics
        stats = {
            "total_books": len(books),
            "total_authors": len(authors),
            "books_with_pub_year": len([b for b in books if b.get("publication_year")]),
            "authors_with_nationality": len([a for a in authors if a.get("nationality")]),
            "authors_with_wikidata": len([a for a in authors if a.get("wikidata_id")]),
            "books_with_awards": len({ba["book_id"] for ba in book_awards}),
            "total_awards": len(book_awards),
        }

        return {
            "books": books,
            "authors": authors,
            "book_awards": book_awards,
            "books_per_author": books_per_author,
            "stats": stats,
        }

    except Exception as e:
        st.error(f"Error loading reading statistics: {e}")
        return {
            "books": [],
            "authors": [],
            "book_awards": [],
            "books_per_author": [],
            "stats": {},
        }
    finally:
        adapter.close()


def main():
    st.title("📈 Reading Statistics")
    st.markdown("*Temporal patterns, demographics, and publication analysis*")

    # Load data
    with st.spinner("Loading reading statistics..."):
        data = load_reading_stats()

    books = data["books"]
    authors = data["authors"]
    book_awards = data["book_awards"]
    books_per_author = data["books_per_author"]
    stats = data["stats"]

    if not books:
        st.warning(
            "No books found in database. "
            "Load your data first:\n\n"
            "```bash\n"
            "load-db load --index-dir data/index\n"
            "```"
        )
        return

    # Overview statistics
    st.header("Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Books", stats["total_books"])

    with col2:
        st.metric("Total Authors", stats["total_authors"])

    with col3:
        st.metric("Award Winners", stats["books_with_awards"])

    # Temporal Analysis
    # Filter books with read dates
    dated_books = [b for b in books if b.get("date_read")]

    if dated_books:
        # Parse dates
        try:
            book_dates = []
            for book in dated_books:
                try:
                    date = datetime.fromisoformat(book["date_read"])
                    book_dates.append((book, date))
                except (ValueError, TypeError):
                    continue

            book_dates.sort(key=lambda x: x[1])

            if book_dates:
                st.subheader("Reading Activity Over Time")

                col1, col2 = st.columns([3, 1])

                with col2:
                    granularity = st.selectbox(
                        "Group by",
                        ["Year", "Quarter", "Month"],
                        help="Choose time period granularity",
                    )

                # Group by selected period
                period_counts = defaultdict(int)
                for _book, date in book_dates:
                    if granularity == "Year":
                        period = date.strftime("%Y")
                    elif granularity == "Quarter":
                        quarter = (date.month - 1) // 3 + 1
                        period = f"{date.year} Q{quarter}"
                    else:  # Month
                        period = date.strftime("%Y-%m")
                    period_counts[period] += 1

                with col1:
                    # Create chart
                    df = pd.DataFrame(list(period_counts.items()), columns=["Period", "Books Read"])
                    df = df.sort_values("Period")
                    st.bar_chart(df.set_index("Period"), height=300)

                # Reading velocity
                st.subheader("Reading Velocity")

                if len(book_dates) >= 2:
                    earliest = book_dates[0][1]
                    latest = book_dates[-1][1]
                    days = (latest - earliest).days

                    if days > 0:
                        books_per_year = len(book_dates) / (days / 365.25)
                        books_per_month = books_per_year / 12

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Time Span", f"{days} days")
                        with col2:
                            st.metric("Avg. per Year", f"{books_per_year:.1f}")
                        with col3:
                            st.metric("Avg. per Month", f"{books_per_month:.1f}")
        except Exception as e:
            st.error(f"Error processing reading dates: {e}")
    else:
        st.info(
            "No books with read dates found. Reading dates are extracted from git history "
            "when books are first added to your notes."
        )

    # Author Demographics
    st.header("Author Demographics")

    # Nationality distribution
    authors_with_nationality = [a for a in authors if a.get("nationality")]
    if authors_with_nationality:
        st.subheader("Authors by Nationality")

        nationality_counts = defaultdict(int)
        for author in authors_with_nationality:
            nationality = author["nationality"]
            if nationality:
                nationality_counts[nationality] += 1

        # Show top nationalities
        top_n = st.slider(
            "Number of nationalities to show",
            min_value=5,
            max_value=min(30, len(nationality_counts)),
            value=15,
            help="Show top N nationalities by author count",
        )

        sorted_nationalities = sorted(nationality_counts.items(), key=lambda x: x[1], reverse=True)[
            :top_n
        ]

        nationality_data = dict(sorted_nationalities)
        st.bar_chart(nationality_data)

        # Summary
        total_nationalities = len(nationality_counts)
        st.markdown(
            f"**{len(authors_with_nationality)} authors** from **{total_nationalities} countries**"
        )

    # Author lifespan analysis
    authors_with_dates = [a for a in authors if a.get("birth_year") or a.get("death_year")]
    if authors_with_dates:
        st.subheader("Author Lifespan Distribution")

        # Calculate lifespans
        lifespans = []
        for author in authors_with_dates:
            if author.get("birth_year") and author.get("death_year"):
                lifespan = author["death_year"] - author["birth_year"]
                if 0 < lifespan < 120:  # Sanity check
                    lifespans.append(lifespan)

        if lifespans:
            avg_lifespan = sum(lifespans) / len(lifespans)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Authors with Lifespans", len(lifespans))
            with col2:
                st.metric("Average Lifespan", f"{avg_lifespan:.1f} years")
            with col3:
                st.metric("Range", f"{min(lifespans)} - {max(lifespans)} years")

    # Publication Era Analysis
    st.header("Publication Era Analysis")

    books_with_pub_year = [b for b in books if b.get("publication_year")]
    if books_with_pub_year:
        st.subheader("Books by Publication Era")

        # Group by century/era
        era_counts = defaultdict(int)
        century_counts = defaultdict(int)

        for book in books_with_pub_year:
            year = book["publication_year"]

            # Century grouping
            if year < 1800:
                century = "Pre-1800"
            elif year < 1900:
                century = "19th Century"
            elif year < 2000:
                century = "20th Century"
            else:
                century = "21st Century"
            century_counts[century] += 1

            # Decade grouping
            decade = (year // 10) * 10
            era_counts[f"{decade}s"] += 1

        # Show century distribution
        st.markdown("**By Century:**")
        century_order = ["Pre-1800", "19th Century", "20th Century", "21st Century"]
        century_data = {c: century_counts.get(c, 0) for c in century_order}
        st.bar_chart(century_data)

        # Show decade distribution (top decades)
        st.markdown("**By Decade:**")
        top_decades = sorted(era_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        decade_data = dict(top_decades)
        st.bar_chart(decade_data)

        # Publication age analysis
        st.subheader("Book Age When Read")

        # Filter books with both publication year and date_read
        books_with_both_dates = [b for b in books_with_pub_year if b.get("date_read")]

        if books_with_both_dates:
            ages = []
            for book in books_with_both_dates:
                try:
                    read_year = datetime.fromisoformat(book["date_read"]).year
                    pub_year = book["publication_year"]
                    age = read_year - pub_year
                    if -5 < age < 500:  # Sanity check
                        ages.append((book["title"], age))
                except (ValueError, TypeError):
                    continue

            if ages:
                avg_age = sum(age for _, age in ages) / len(ages)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Books Analyzed", len(ages))
                with col2:
                    st.metric("Avg. Age When Read", f"{avg_age:.1f} years")
                with col3:
                    oldest = max(ages, key=lambda x: x[1])
                    st.metric("Oldest Book Read", f"{oldest[1]} years")

                # Show distribution
                age_ranges = {
                    "0-5 years": len([a for _, a in ages if 0 <= a <= 5]),
                    "6-10 years": len([a for _, a in ages if 6 <= a <= 10]),
                    "11-25 years": len([a for _, a in ages if 11 <= a <= 25]),
                    "26-50 years": len([a for _, a in ages if 26 <= a <= 50]),
                    "51-100 years": len([a for _, a in ages if 51 <= a <= 100]),
                    "100+ years": len([a for _, a in ages if a > 100]),
                }

                st.bar_chart(age_ranges)

    # Books Per Author
    if books_per_author:
        st.header("Books Per Author")

        top_n = st.slider(
            "Number of authors to show",
            min_value=5,
            max_value=min(30, len(books_per_author)),
            value=15,
            key="books_per_author_slider",
            help="Show top N authors by book count",
        )

        # Create chart data
        top_authors = books_per_author[:top_n]
        author_data = {a["name"]: a["book_count"] for a in top_authors}
        st.bar_chart(author_data)

        # Summary stats
        total_authors = len(books_per_author)
        books_per_author_avg = sum(a["book_count"] for a in books_per_author) / total_authors

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Authors", total_authors)
        with col2:
            st.metric("Avg. Books per Author", f"{books_per_author_avg:.1f}")
        with col3:
            most_read = books_per_author[0]
            st.metric("Most Read Author", f"{most_read['name']} ({most_read['book_count']})")

    # Awards Analysis
    if book_awards:
        st.header("Award-Winning Books")

        st.subheader("Books with Awards")

        # Group awards by book
        books_awards = defaultdict(list)
        for ba in book_awards:
            books_awards[ba["book_id"]].append(
                {"award": ba["award_name"], "year": ba.get("year_awarded")}
            )

        # Display award-winning books
        award_books_data = []
        for book_id, awards_list in books_awards.items():
            book = next((b for b in books if b["id"] == book_id), None)
            if book:
                awards_str = ", ".join(
                    f"{a['award']}" + (f" ({a['year']})" if a.get("year") else "")
                    for a in awards_list
                )
                award_books_data.append(
                    {
                        "Title": book["title"],
                        "Author": book.get("author_name", "Unknown"),
                        "Awards": awards_str,
                        "Count": len(awards_list),
                    }
                )

        # Sort by award count
        award_books_data.sort(key=lambda x: x["Count"], reverse=True)

        df = pd.DataFrame(award_books_data)
        st.dataframe(df.drop(columns=["Count"]), hide_index=True, width="stretch")

        # Award statistics
        st.subheader("Award Statistics")

        # Count awards by type
        award_counts = defaultdict(int)
        for ba in book_awards:
            award_counts[ba["award_name"]] += 1

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Most Common Awards:**")
            sorted_awards = sorted(award_counts.items(), key=lambda x: x[1], reverse=True)
            for award, count in sorted_awards[:10]:
                st.markdown(f"- {award}: {count} books")

        with col2:
            st.metric("Total Award-Winning Books", len(books_awards))
            st.metric("Total Awards", len(book_awards))
            st.metric("Unique Award Types", len(award_counts))
    else:
        st.info("No award data found. Enrich with Wikidata to add award information.")


if __name__ == "__main__":
    main()
