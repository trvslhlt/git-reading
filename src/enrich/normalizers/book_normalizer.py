"""Book metadata normalizer for Open Library API responses."""

from typing import Any

from .base import Normalizer


class BookNormalizer(Normalizer):
    """Normalize Open Library book metadata to database schema format.

    Handles the complex structure of Open Library API responses and extracts
    relevant fields for our database schema.
    """

    def normalize(self, api_response: dict[str, Any], source: str) -> dict[str, Any]:
        """Convert Open Library API response to database schema format.

        Args:
            api_response: Raw Open Library API response
            source: Should be 'openlibrary'

        Returns:
            Normalized dictionary with keys matching database columns:
                - isbn_10: ISBN-10 identifier
                - isbn_13: ISBN-13 identifier
                - publication_year: Year of publication
                - publisher: Publisher name
                - page_count: Number of pages
                - language: Language code (e.g., 'en')
                - description: Book description
                - cover_url: Cover image URL
                - openlibrary_id: Open Library work ID
                - subjects: List of subject strings

        Raises:
            ValueError: If API response is malformed
        """
        if source != "openlibrary":
            raise ValueError(f"BookNormalizer only handles 'openlibrary' source, got '{source}'")

        # Extract ISBNs from various possible locations
        isbn_10 = self._extract_isbn_10(api_response)
        isbn_13 = self._extract_isbn_13(api_response)

        # Use isbn_13 for the legacy 'isbn' field if available
        isbn = isbn_13 or isbn_10

        # Extract publication year
        publication_year = self._extract_publication_year(api_response)

        # Extract publisher (may be in multiple locations)
        publisher = self._extract_publisher(api_response)

        # Extract page count
        page_count = self._extract_page_count(api_response)

        # Extract language
        language = self._extract_language(api_response)

        # Extract description
        description = self._extract_description(api_response)

        # Extract cover URL
        cover_url = self._extract_cover_url(api_response)

        # Extract Open Library ID
        openlibrary_id = self._extract_openlibrary_id(api_response)

        # Extract subjects
        subjects = self._extract_subjects(api_response)

        return {
            "isbn": isbn,
            "isbn_10": isbn_10,
            "isbn_13": isbn_13,
            "publication_year": publication_year,
            "publisher": publisher,
            "page_count": page_count,
            "language": language,
            "description": description,
            "cover_url": cover_url,
            "openlibrary_id": openlibrary_id,
            "subjects": subjects,
        }

    def _extract_isbn_10(self, data: dict[str, Any]) -> str | None:
        """Extract ISBN-10 from API response."""
        # Try edition data first
        edition = data.get("edition", {})
        isbn_10_list = edition.get("isbn_10", [])
        if isbn_10_list and len(isbn_10_list) > 0:
            return isbn_10_list[0]

        # Try search result
        isbn_list = data.get("isbn", [])
        for isbn in isbn_list:
            if len(isbn) == 10:
                return isbn

        return None

    def _extract_isbn_13(self, data: dict[str, Any]) -> str | None:
        """Extract ISBN-13 from API response."""
        # Try edition data first
        edition = data.get("edition", {})
        isbn_13_list = edition.get("isbn_13", [])
        if isbn_13_list and len(isbn_13_list) > 0:
            return isbn_13_list[0]

        # Try search result
        isbn_list = data.get("isbn", [])
        for isbn in isbn_list:
            if len(isbn) == 13:
                return isbn

        return None

    def _extract_publication_year(self, data: dict[str, Any]) -> int | None:
        """Extract publication year from API response."""
        # Try first_publish_year (from search results)
        first_year = data.get("first_publish_year")
        if first_year:
            return int(first_year)

        # Try publish_date from edition
        edition = data.get("edition", {})
        publish_date = edition.get("publish_date")
        if publish_date:
            year = self._extract_year(publish_date)
            if year:
                return year

        # Try publish_year array
        publish_years = data.get("publish_year", [])
        if publish_years:
            return self._extract_year(str(publish_years[0]))

        return None

    def _extract_publisher(self, data: dict[str, Any]) -> str | None:
        """Extract publisher name from API response."""
        # Try edition data
        edition = data.get("edition", {})
        publishers = edition.get("publishers", [])
        if publishers:
            # Handle both string and dict publishers
            first_pub = publishers[0]
            if isinstance(first_pub, dict):
                return first_pub.get("name")
            return str(first_pub)

        # Try search result
        publisher_list = data.get("publisher", [])
        if publisher_list:
            return str(publisher_list[0])

        return None

    def _extract_page_count(self, data: dict[str, Any]) -> int | None:
        """Extract page count from API response."""
        # Try edition data
        edition = data.get("edition", {})
        num_pages = edition.get("number_of_pages")
        if num_pages:
            try:
                return int(num_pages)
            except (ValueError, TypeError):
                pass

        # Try search result
        num_pages = data.get("number_of_pages_median")
        if num_pages:
            try:
                return int(num_pages)
            except (ValueError, TypeError):
                pass

        return None

    def _extract_language(self, data: dict[str, Any]) -> str | None:
        """Extract language code from API response."""
        # Try edition data
        edition = data.get("edition", {})
        languages = edition.get("languages", [])
        if languages:
            # Languages can be keys like "/languages/eng"
            lang = languages[0]
            if isinstance(lang, dict):
                lang_key = lang.get("key", "")
            else:
                lang_key = str(lang)

            # Extract language code from key
            if "/" in lang_key:
                return lang_key.split("/")[-1]
            return lang_key

        # Try search result
        lang_list = data.get("language", [])
        if lang_list:
            return str(lang_list[0])

        return None

    def _extract_description(self, data: dict[str, Any]) -> str | None:
        """Extract book description from API response."""
        # Try description from work data
        description = data.get("description")
        if description:
            # Description can be string or dict with "value" key
            if isinstance(description, dict):
                return description.get("value")
            return str(description)

        # Try first_sentence
        first_sentence = data.get("first_sentence")
        if first_sentence:
            if isinstance(first_sentence, dict):
                return first_sentence.get("value")
            return str(first_sentence)

        return None

    def _extract_cover_url(self, data: dict[str, Any]) -> str | None:
        """Extract cover image URL from API response."""
        # Try cover_id from search results
        cover_id = data.get("cover_i")
        if cover_id:
            return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

        # Try covers array from work data
        covers = data.get("covers", [])
        if covers and covers[0]:
            return f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg"

        # Try edition data
        edition = data.get("edition", {})
        edition_covers = edition.get("covers", [])
        if edition_covers and edition_covers[0]:
            return f"https://covers.openlibrary.org/b/id/{edition_covers[0]}-L.jpg"

        return None

    def _extract_openlibrary_id(self, data: dict[str, Any]) -> str | None:
        """Extract Open Library work ID from API response."""
        # Try work_key (added by our client)
        work_key = data.get("work_key")
        if work_key:
            # Remove /works/ prefix if present
            if work_key.startswith("/works/"):
                return work_key[7:]
            return work_key

        # Try key field
        key = data.get("key")
        if key:
            if key.startswith("/works/"):
                return key[7:]
            return key

        return None

    def _extract_subjects(self, data: dict[str, Any]) -> list[str]:
        """Extract subject tags from API response."""
        subjects = set()

        # Try subject array from work data
        subject_list = data.get("subjects", [])
        for subject in subject_list:
            if isinstance(subject, dict):
                subjects.add(subject.get("name", ""))
            else:
                subjects.add(str(subject))

        # Try subject from search results
        search_subjects = data.get("subject", [])
        subjects.update(str(s) for s in search_subjects)

        # Filter out empty strings
        return sorted([s for s in subjects if s.strip()])
