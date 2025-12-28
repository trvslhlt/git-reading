"""High-level orchestration for enrichment workflows."""

import hashlib
from typing import Any

from common.logger import get_logger
from load.db import DatabaseAdapter, IntegrityError, get_adapter

from .clients.base import APIError, NoMatchError
from .clients.openlibrary import OpenLibraryClient
from .clients.wikidata import WikidataClient
from .normalizers.book_normalizer import BookNormalizer
from .normalizers.wikidata_normalizer import WikidataAuthorNormalizer, WikidataBookNormalizer
from .source_tracker import SourceTracker

logger = get_logger(__name__)


class EnrichmentOrchestrator:
    """Orchestrate the enrichment workflow for books and authors.

    This class coordinates API clients, normalizers, and database operations
    to enrich book and author metadata while tracking data provenance.
    """

    def __init__(self, adapter: DatabaseAdapter | None = None, sources: list[str] | None = None):
        """Initialize orchestrator.

        Args:
            adapter: Database adapter (if None, creates one from env)
            sources: List of data sources to use (default: ['openlibrary'])
        """
        self.adapter = adapter or get_adapter()
        self.source_tracker = SourceTracker(self.adapter)
        self.sources = sources or ["openlibrary"]

        # Initialize clients based on requested sources
        self.openlibrary_client = OpenLibraryClient() if "openlibrary" in self.sources else None
        self.wikidata_client = WikidataClient() if "wikidata" in self.sources else None

        # Initialize normalizers
        self.book_normalizer = BookNormalizer()
        self.wikidata_book_normalizer = WikidataBookNormalizer()
        self.wikidata_author_normalizer = WikidataAuthorNormalizer()

    def enrich_books(self, limit: int | None = None) -> dict[str, int]:
        """Enrich all unenriched books in the database.

        Args:
            limit: Maximum number of books to enrich (None = all)

        Returns:
            Dictionary with statistics:
                - attempted: Number of books attempted
                - successful: Number successfully enriched
                - failed: Number that failed
                - skipped: Number skipped (already enriched)

        Note:
            Each book is committed individually to prevent transaction errors
            from affecting subsequent books.

        Example:
            >>> orchestrator = EnrichmentOrchestrator()
            >>> stats = orchestrator.enrich_books(limit=10)
            >>> print(f"Enriched {stats['successful']}/{stats['attempted']} books")
        """
        stats = {"attempted": 0, "successful": 0, "failed": 0, "skipped": 0}

        # Get unenriched books (where isbn_13 is NULL)
        query = "SELECT id, title FROM books WHERE isbn_13 IS NULL"
        if limit:
            query += f" LIMIT {limit}"

        books = self.adapter.fetchall(query)

        if not books:
            logger.info("No unenriched books found")
            return stats

        logger.info(f"Found {len(books)} book(s) to enrich")

        for i, book in enumerate(books):
            book_id = book["id"]
            title = book["title"]

            try:
                # Get author(s) for this book
                authors = self.adapter.fetchall(
                    """
                    SELECT a.name, a.first_name, a.last_name
                    FROM authors a
                    JOIN book_authors ba ON a.id = ba.author_id
                    WHERE ba.book_id = ?
                    """,
                    (book_id,),
                )

                if not authors:
                    logger.warning(f"Book '{title}' (ID: {book_id}) has no authors, skipping")
                    stats["skipped"] += 1
                    continue

                # Use first author for search
                author_name = authors[0]["name"]

                logger.info(f"[{i + 1}/{len(books)}] Enriching '{title}' by {author_name}")

                success = self.enrich_book(book_id, title, author_name)
                stats["attempted"] += 1
                if success:
                    stats["successful"] += 1
                    # Commit immediately after successful enrichment
                    self.adapter.commit()
                else:
                    stats["failed"] += 1
                    # Ensure transaction is clean after failure
                    try:
                        self.adapter.rollback()
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"Unexpected error enriching '{title}': {e}")
                stats["attempted"] += 1
                stats["failed"] += 1
                # Rollback the failed transaction before continuing
                try:
                    self.adapter.rollback()
                except Exception:
                    pass  # Ignore rollback errors
                continue

        logger.info(
            f"\n[green]✓[/green] Enrichment complete!\n"
            f"  Attempted: {stats['attempted']}\n"
            f"  Successful: {stats['successful']}\n"
            f"  Failed: {stats['failed']}\n"
            f"  Skipped: {stats['skipped']}"
        )

        return stats

    def enrich_book(self, book_id: str, title: str, author: str) -> bool:
        """Enrich a single book with metadata from configured sources.

        Args:
            book_id: Database ID of the book
            title: Book title
            author: Author name

        Returns:
            True if enrichment was successful from at least one source, False otherwise

        Raises:
            APIError: If API request fails catastrophically
        """
        success = False

        # Try Open Library first (if enabled)
        if "openlibrary" in self.sources and self.openlibrary_client:
            try:
                success = self._enrich_book_openlibrary(book_id, title, author) or success
            except APIError as e:
                logger.error(f"✗ Open Library API error for '{title}': {e}")

        # Then try Wikidata (if enabled)
        if "wikidata" in self.sources and self.wikidata_client:
            try:
                success = self._enrich_book_wikidata(book_id, title, author) or success
            except APIError as e:
                logger.error(f"✗ Wikidata API error for '{title}': {e}")

        return success

    def _enrich_book_openlibrary(self, book_id: str, title: str, author: str) -> bool:
        """Enrich a single book with metadata from Open Library.

        Args:
            book_id: Database ID of the book
            title: Book title
            author: Author name

        Returns:
            True if enrichment was successful, False otherwise
        """
        try:
            # Search Open Library
            api_response = self.openlibrary_client.search_book(title, author)

            if not api_response:
                logger.debug(f"✗ No Open Library match for '{title}' by {author}")
                return False

            # Normalize API response
            normalized_data = self.book_normalizer.normalize(api_response, "openlibrary")

            # Update book record
            self._update_book_fields(book_id, normalized_data, source="openlibrary")

            # Handle subjects (many-to-many relationship)
            subjects = normalized_data.get("subjects", [])
            if subjects:
                self._add_book_subjects(book_id, subjects, source="openlibrary")

            logger.info(
                f"✓ Open Library: "
                f"ISBN-13: {normalized_data.get('isbn_13', 'N/A')}, "
                f"Year: {normalized_data.get('publication_year', 'N/A')}, "
                f"Subjects: {len(subjects)}"
            )

            return True

        except NoMatchError:
            logger.debug(f"✗ No Open Library match for '{title}' by {author}")
            return False

        except Exception as e:
            logger.error(f"✗ Open Library error for '{title}': {e}")
            return False

    def _enrich_book_wikidata(self, book_id: str, title: str, author: str) -> bool:
        """Enrich a single book with metadata from Wikidata.

        Args:
            book_id: Database ID of the book
            title: Book title
            author: Author name

        Returns:
            True if enrichment was successful, False otherwise
        """
        try:
            # First try to find by ISBN if we have one
            book_data = self.adapter.fetchone(
                "SELECT isbn_13, isbn_10 FROM books WHERE id = ?", (book_id,)
            )
            isbn = book_data.get("isbn_13") or book_data.get("isbn_10") if book_data else None

            api_response = None
            if isbn:
                api_response = self.wikidata_client.search_book_by_isbn(isbn)

            # Fall back to title/author search if ISBN search failed
            if not api_response:
                api_response = self.wikidata_client.search_book_by_title_author(title, author)

            if not api_response:
                logger.debug(f"✗ No Wikidata match for '{title}' by {author}")
                return False

            # Normalize API response
            normalized_data = self.wikidata_book_normalizer.normalize(api_response, "wikidata")

            # Update book record
            self._update_book_fields(book_id, normalized_data, source="wikidata")

            # Handle subjects
            subjects = normalized_data.get("subjects", [])
            if subjects:
                self._add_book_subjects(book_id, subjects, source="wikidata")

            # Handle literary movements
            movements = normalized_data.get("literary_movements", [])
            if movements:
                logger.debug(
                    f"Found {len(movements)} literary movements (Phase 2.2 implementation pending)"
                )

            logger.info(
                f"✓ Wikidata: "
                f"ID: {normalized_data.get('wikidata_id', 'N/A')}, "
                f"Subjects: {len(subjects)}, "
                f"Movements: {len(movements)}"
            )

            return True

        except NoMatchError:
            logger.debug(f"✗ No Wikidata match for '{title}' by {author}")
            return False

        except Exception as e:
            logger.error(f"✗ Wikidata error for '{title}': {e}")
            return False

    def _update_book_fields(
        self, book_id: str, normalized_data: dict[str, Any], source: str
    ) -> None:
        """Update book fields in database and log enrichment.

        Args:
            book_id: Book ID
            normalized_data: Normalized book metadata
            source: Data source ('openlibrary', 'wikidata', etc.)
        """
        # Fields to update (excluding subjects which are handled separately)
        # Map source to specific ID field
        source_id_fields = {
            "openlibrary": "openlibrary_id",
            "wikidata": "wikidata_id",
        }

        fields = [
            "isbn",
            "isbn_10",
            "isbn_13",
            "publication_year",
            "publisher",
            "page_count",
            "language",
            "description",
            "cover_url",
        ]

        # Add source-specific ID field
        if source in source_id_fields:
            fields.append(source_id_fields[source])

        # Build UPDATE query dynamically for non-null fields
        updates = []
        params = []
        for field in fields:
            value = normalized_data.get(field)
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(value)

                # Determine API endpoint based on source
                api_endpoint = {
                    "openlibrary": OpenLibraryClient.SEARCH_URL,
                    "wikidata": WikidataClient.SPARQL_ENDPOINT,
                }.get(source, "unknown")

                # Log enrichment
                self.source_tracker.log_enrichment(
                    entity_type="book",
                    entity_id=book_id,
                    field_name=field,
                    new_value=value,
                    source=source,
                    method="api",
                    api_endpoint=api_endpoint,
                )

        if not updates:
            return

        # Add updated_at timestamp
        updates.append("updated_at = CURRENT_TIMESTAMP")

        # Execute update
        params.append(book_id)
        query = f"UPDATE books SET {', '.join(updates)} WHERE id = ?"

        self.adapter.execute(query, tuple(params))

    def _add_book_subjects(self, book_id: str, subjects: list[str], source: str) -> None:
        """Add subjects to book with source tracking.

        Args:
            book_id: Book ID
            subjects: List of subject strings
            source: Source identifier ('openlibrary', etc.)
        """
        for subject_name in subjects:
            if not subject_name.strip():
                continue

            # Get or create subject
            subject_id = self._get_or_create_subject(subject_name)

            # Link book to subject with source tracking
            try:
                self.adapter.execute(
                    """
                    INSERT INTO book_subjects (book_id, subject_id, source)
                    VALUES (?, ?, ?)
                    ON CONFLICT(book_id, subject_id) DO UPDATE SET
                        source = excluded.source,
                        added_at = CURRENT_TIMESTAMP
                    """,
                    (book_id, subject_id, source),
                )
            except IntegrityError:
                # Already exists, that's fine
                pass

    def _get_or_create_subject(self, subject_name: str) -> str:
        """Get existing subject ID or create new subject.

        Args:
            subject_name: Subject name

        Returns:
            Subject ID
        """
        # Generate deterministic ID from name
        subject_id = self._generate_subject_id(subject_name)

        # Try to insert (will fail if exists on either id or name)
        try:
            self.adapter.execute(
                """
                INSERT INTO subjects (id, name)
                VALUES (?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (subject_id, subject_name),
            )
        except IntegrityError:
            # Subject already exists (name conflict)
            pass

        return subject_id

    def _generate_subject_id(self, subject_name: str) -> str:
        """Generate deterministic subject ID from name.

        Args:
            subject_name: Subject name

        Returns:
            Subject ID (hash-based)
        """
        # Use SHA256 hash of normalized name
        normalized = subject_name.lower().strip()
        hash_digest = hashlib.sha256(normalized.encode()).hexdigest()
        return f"subject:{hash_digest[:16]}"

    def get_enrichment_coverage(self) -> dict[str, Any]:
        """Get statistics about enrichment coverage.

        Returns:
            Dictionary with coverage statistics:
                - total_books: Total number of books
                - isbn_13_count: Books with ISBN-13
                - publication_year_count: Books with publication year
                - subjects_count: Books with subjects
                - avg_subjects_per_book: Average subjects per book

        Example:
            >>> stats = orchestrator.get_enrichment_coverage()
            >>> print(f"ISBN-13 coverage: {stats['isbn_13_count']}/{stats['total_books']}")
        """
        total_books = self.adapter.fetchscalar("SELECT COUNT(*) FROM books")

        isbn_13_count = self.adapter.fetchscalar(
            "SELECT COUNT(*) FROM books WHERE isbn_13 IS NOT NULL"
        )

        pub_year_count = self.adapter.fetchscalar(
            "SELECT COUNT(*) FROM books WHERE publication_year IS NOT NULL"
        )

        books_with_subjects = self.adapter.fetchscalar(
            """
            SELECT COUNT(DISTINCT book_id)
            FROM book_subjects
            """
        )

        total_subject_links = self.adapter.fetchscalar("SELECT COUNT(*) FROM book_subjects")

        avg_subjects = (
            round(total_subject_links / books_with_subjects, 1) if books_with_subjects > 0 else 0
        )

        return {
            "total_books": total_books,
            "isbn_13_count": isbn_13_count,
            "isbn_13_percent": round(isbn_13_count / total_books * 100, 1) if total_books else 0,
            "publication_year_count": pub_year_count,
            "publication_year_percent": (
                round(pub_year_count / total_books * 100, 1) if total_books else 0
            ),
            "books_with_subjects": books_with_subjects,
            "subjects_percent": (
                round(books_with_subjects / total_books * 100, 1) if total_books else 0
            ),
            "avg_subjects_per_book": avg_subjects,
        }

    def close(self) -> None:
        """Clean up resources."""
        if self.openlibrary_client:
            self.openlibrary_client.close()
        if self.wikidata_client:
            self.wikidata_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
