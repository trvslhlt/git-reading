"""Abstract base class for API clients."""

from abc import ABC, abstractmethod
from typing import Any


class APIClient(ABC):
    """Base class for all external API clients.

    All API client implementations (Open Library, Wikidata, etc.) must
    implement this interface to ensure consistent behavior.
    """

    @abstractmethod
    def search_book(self, title: str, author: str) -> dict[str, Any] | None:
        """Search for a book by title and author.

        Args:
            title: Book title
            author: Author name (full name or last name)

        Returns:
            Raw API response as dictionary, or None if not found

        Raises:
            APIError: If API request fails
            RateLimitError: If rate limit is exceeded
        """
        pass

    @abstractmethod
    def search_author(self, name: str) -> dict[str, Any] | None:
        """Search for an author by name.

        Args:
            name: Author name (full name preferred)

        Returns:
            Raw API response as dictionary, or None if not found

        Raises:
            APIError: If API request fails
            RateLimitError: If rate limit is exceeded
        """
        pass

    @abstractmethod
    def get_rate_limit(self) -> tuple[int, int]:
        """Get rate limit configuration for this API.

        Returns:
            Tuple of (requests_per_period, period_seconds)
            Example: (60, 60) means 60 requests per 60 seconds
        """
        pass


class EnrichmentError(Exception):
    """Base exception for enrichment errors."""

    pass


class APIError(EnrichmentError):
    """API request failed."""

    pass


class NoMatchError(EnrichmentError):
    """No match found for the given search criteria."""

    pass


class RateLimitError(EnrichmentError):
    """Rate limit exceeded."""

    pass
