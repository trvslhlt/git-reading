"""Abstract base class for data normalizers."""

from abc import ABC, abstractmethod
from typing import Any


class Normalizer(ABC):
    """Base class for API response normalizers.

    Normalizers convert external API responses into our internal database schema format.
    Each API source has its own normalizer to handle its specific response structure.
    """

    @abstractmethod
    def normalize(self, api_response: dict[str, Any], source: str) -> dict[str, Any]:
        """Convert API response to database schema format.

        Args:
            api_response: Raw API response dictionary
            source: Source identifier (e.g., 'openlibrary', 'wikidata')

        Returns:
            Normalized data dictionary ready for database insertion.
            Keys should match database column names.

        Raises:
            ValueError: If API response is malformed or missing required fields
        """
        pass

    def _safe_get(self, data: dict[str, Any], *keys: str, default: Any = None) -> Any:
        """Safely navigate nested dictionary keys.

        Args:
            data: Dictionary to navigate
            *keys: Sequence of keys to traverse
            default: Default value if key path doesn't exist

        Returns:
            Value at the key path, or default if not found

        Example:
            >>> self._safe_get({'a': {'b': {'c': 1}}}, 'a', 'b', 'c')
            1
            >>> self._safe_get({'a': {}}, 'a', 'b', 'c', default='missing')
            'missing'
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _extract_year(self, date_str: str | None) -> int | None:
        """Extract year from various date string formats.

        Args:
            date_str: Date string (e.g., '2020', '2020-01-15', 'January 2020')

        Returns:
            Year as integer, or None if extraction fails

        Example:
            >>> self._extract_year('2020-01-15')
            2020
            >>> self._extract_year('2020')
            2020
            >>> self._extract_year(None)
            None
        """
        if not date_str:
            return None

        # Try direct integer conversion
        try:
            return int(date_str)
        except ValueError:
            pass

        # Try extracting first 4-digit number
        import re

        match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", str(date_str))
        if match:
            return int(match.group(1))

        return None
