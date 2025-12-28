"""Open Library API client for book metadata enrichment."""

from typing import Any

import requests

from common.logger import get_logger

from .base import APIClient, APIError, RateLimitError
from .rate_limiter import RateLimiter

logger = get_logger(__name__)


class OpenLibraryClient(APIClient):
    """Client for the Open Library API.

    Open Library provides free access to book metadata including:
    - ISBNs (ISBN-10 and ISBN-13)
    - Publication information (year, publisher, page count)
    - Subjects and genres
    - Cover images
    - Author information

    Rate limit: Conservative 60 requests per minute (unofficial limit).

    API Documentation: https://openlibrary.org/dev/docs/api/books
    """

    BASE_URL = "https://openlibrary.org"
    SEARCH_URL = f"{BASE_URL}/search.json"
    BOOKS_URL = f"{BASE_URL}/books"
    AUTHORS_URL = f"{BASE_URL}/authors"

    def __init__(self, requests_per_minute: int = 60):
        """Initialize Open Library client.

        Args:
            requests_per_minute: Rate limit (default: 60 requests per minute)
        """
        self.rate_limiter = RateLimiter(
            requests_per_period=requests_per_minute,
            period_seconds=60,
        )
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "git-reading/1.0 (https://github.com/trvslhlt/git-reading)"}
        )

    def search_book(self, title: str, author: str) -> dict[str, Any] | None:
        """Search for a book by title and author.

        Args:
            title: Book title
            author: Author name

        Returns:
            Raw API response with book metadata, or None if not found

        Raises:
            APIError: If API request fails
            RateLimitError: If rate limit is exceeded
        """
        # Try multiple title variations to handle subtitles, punctuation, etc.
        title_variations = self._generate_title_variations(title)

        for i, title_variant in enumerate(title_variations):
            if i > 0:
                # Wait before retry to respect rate limits
                self.rate_limiter.wait_if_needed()

            try:
                result = self._search_book_exact(title_variant, author)
                if result:
                    if i > 0:
                        logger.debug(
                            f"Found match using title variation '{title_variant}' "
                            f"(original: '{title}')"
                        )
                    return result
            except APIError:
                # Re-raise API errors immediately
                raise

        logger.debug(
            f"No results found for '{title}' by {author} (tried {len(title_variations)} variations)"
        )
        return None

    def _generate_title_variations(self, title: str) -> list[str]:
        """Generate title variations to try for better matching.

        Args:
            title: Original book title

        Returns:
            List of title variations to try, in order of preference

        Example:
            >>> client._generate_title_variations("Money: A Suicide Note")
            ['Money: A Suicide Note', 'Money']
        """
        variations = [title]  # Always try the original first

        # Try removing subtitle (everything after : or —)
        for separator in [":", "—", " - "]:
            if separator in title:
                main_title = title.split(separator)[0].strip()
                if main_title and main_title not in variations:
                    variations.append(main_title)

        return variations

    def _search_book_exact(self, title: str, author: str) -> dict[str, Any] | None:
        """Search for a book with exact title.

        Args:
            title: Book title
            author: Author name

        Returns:
            Raw API response with book metadata, or None if not found

        Raises:
            APIError: If API request fails
        """
        self.rate_limiter.wait_if_needed()

        try:
            params = {
                "title": title,
                "author": author,
                "limit": 5,  # Get top 5 results for fuzzy matching
            }

            logger.debug(f"Searching Open Library for '{title}' by {author}")
            response = self.session.get(self.SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            docs = data.get("docs", [])

            if not docs:
                return None

            # Return the best match (first result is usually best)
            best_match = docs[0]
            logger.debug(
                f"Found match: '{best_match.get('title')}' "
                f"({best_match.get('first_publish_year', 'unknown year')})"
            )

            # Fetch detailed metadata if we have a key
            work_key = best_match.get("key")
            if work_key:
                return self._get_work_details(work_key, best_match)

            return best_match

        except requests.exceptions.Timeout as e:
            raise APIError(f"Open Library API timeout for '{title}'") from e
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response and e.response.status_code == 429:
                raise RateLimitError("Open Library rate limit exceeded") from e
            raise APIError(f"Open Library API error: {e}") from e

    def _get_work_details(self, work_key: str, search_result: dict[str, Any]) -> dict[str, Any]:
        """Fetch detailed work metadata and merge with search results.

        Args:
            work_key: Open Library work key (e.g., '/works/OL45804W')
            search_result: Initial search result to merge with

        Returns:
            Enhanced metadata dictionary
        """
        try:
            url = f"{self.BASE_URL}{work_key}.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            work_data = response.json()

            # Merge search result with detailed work data
            merged = {**search_result, **work_data, "work_key": work_key}

            # Fetch edition data for ISBN, page count, etc.
            edition_key = search_result.get("cover_edition_key")
            if edition_key:
                edition_data = self._get_edition_details(edition_key)
                if edition_data:
                    merged["edition"] = edition_data

            return merged

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch work details for {work_key}: {e}")
            return search_result  # Return search result as fallback

    def _get_edition_details(self, edition_key: str) -> dict[str, Any] | None:
        """Fetch edition-specific metadata (ISBNs, page count, etc.).

        Args:
            edition_key: Open Library edition key (e.g., 'OL7353617M')

        Returns:
            Edition metadata dictionary, or None if fetch fails
        """
        try:
            url = f"{self.BOOKS_URL}/{edition_key}.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.debug(f"Failed to fetch edition {edition_key}: {e}")
            return None

    def search_author(self, name: str) -> dict[str, Any] | None:
        """Search for an author by name.

        Args:
            name: Author name (full name preferred)

        Returns:
            Raw API response with author metadata, or None if not found

        Raises:
            APIError: If API request fails
        """
        self.rate_limiter.wait_if_needed()

        try:
            # Search for author
            params = {"q": name, "type": "author", "limit": 1}

            logger.debug(f"Searching Open Library for author '{name}'")
            response = self.session.get(self.SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            docs = data.get("docs", [])

            if not docs:
                logger.debug(f"No author found for '{name}'")
                return None

            author_data = docs[0]

            # Fetch detailed author data if we have a key
            author_key = author_data.get("key")
            if author_key:
                return self._get_author_details(author_key, author_data)

            return author_data

        except requests.exceptions.Timeout as e:
            raise APIError(f"Open Library API timeout for author '{name}'") from e
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response and e.response.status_code == 429:
                raise RateLimitError("Open Library rate limit exceeded") from e
            raise APIError(f"Open Library API error: {e}") from e

    def _get_author_details(self, author_key: str, search_result: dict[str, Any]) -> dict[str, Any]:
        """Fetch detailed author metadata.

        Args:
            author_key: Open Library author key (e.g., '/authors/OL23919A')
            search_result: Initial search result to merge with

        Returns:
            Enhanced author metadata dictionary
        """
        try:
            url = f"{self.BASE_URL}{author_key}.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            author_data = response.json()
            return {**search_result, **author_data, "author_key": author_key}

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch author details for {author_key}: {e}")
            return search_result

    def get_rate_limit(self) -> tuple[int, int]:
        """Get rate limit configuration.

        Returns:
            Tuple of (60, 60) - 60 requests per 60 seconds
        """
        return (self.rate_limiter.requests_per_period, self.rate_limiter.period_seconds)

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
