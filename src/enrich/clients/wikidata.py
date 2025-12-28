"""Wikidata SPARQL API client for book and author enrichment."""

from typing import Any

import requests

from common.logger import get_logger

from .base import APIClient, APIError, RateLimitError
from .rate_limiter import RateLimiter
from .wikidata_label_resolver import WikidataLabelResolver

logger = get_logger(__name__)


class WikidataClient(APIClient):
    """Client for the Wikidata Query Service (SPARQL endpoint).

    Wikidata provides structured data about:
    - Author biographical data (birth/death dates, nationality)
    - Literary movements and genres
    - Book themes and awards
    - Influence relationships between authors
    - Cross-references (VIAF, Wikipedia, etc.)

    Rate limit: 60 requests per minute (conservative, no official limit but being polite)

    API Documentation: https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/API
    """

    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"

    def __init__(self, requests_per_minute: int = 60):
        """Initialize Wikidata client.

        Args:
            requests_per_minute: Rate limit (default: 60 requests per minute)
        """
        self.rate_limiter = RateLimiter(
            requests_per_period=requests_per_minute,
            period_seconds=60,
        )
        self.label_resolver = WikidataLabelResolver()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "git-reading/1.0 (https://github.com/trvslhlt/git-reading)",
                "Accept": "application/sparql-results+json",
            }
        )

    def search_book_by_isbn(self, isbn: str) -> dict[str, Any] | None:
        """Search for a book in Wikidata by ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Wikidata entity data or None if not found

        Raises:
            APIError: If API request fails
            RateLimitError: If rate limit is exceeded
        """
        self.rate_limiter.wait_if_needed()

        # SPARQL query to find book by ISBN
        query = f"""
        SELECT ?book ?bookLabel ?isbn10 ?isbn13 WHERE {{
          VALUES ?isbn {{ "{isbn}" }}
          {{
            ?book wdt:P957 ?isbn .  # ISBN-10
            OPTIONAL {{ ?book wdt:P957 ?isbn10 }}
            OPTIONAL {{ ?book wdt:P212 ?isbn13 }}
          }} UNION {{
            ?book wdt:P212 ?isbn .  # ISBN-13
            OPTIONAL {{ ?book wdt:P957 ?isbn10 }}
            OPTIONAL {{ ?book wdt:P212 ?isbn13 }}
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 1
        """

        try:
            logger.debug(f"Searching Wikidata for ISBN {isbn}")
            response = self.session.get(
                self.SPARQL_ENDPOINT, params={"query": query, "format": "json"}, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            if not bindings:
                logger.debug(f"No Wikidata results for ISBN {isbn}")
                return None

            # Extract Wikidata ID from URI
            book_uri = bindings[0].get("book", {}).get("value", "")
            if not book_uri:
                return None

            wikidata_id = book_uri.split("/")[-1]  # Extract Q-number
            logger.debug(f"Found Wikidata entity: {wikidata_id}")

            # Fetch full entity data
            return self._get_entity_data(wikidata_id)

        except requests.exceptions.Timeout as e:
            raise APIError(f"Wikidata API timeout for ISBN {isbn}") from e
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response and e.response.status_code == 429:
                raise RateLimitError("Wikidata rate limit exceeded") from e
            raise APIError(f"Wikidata API error: {e}") from e

    def search_book_by_title_author(self, title: str, author: str) -> dict[str, Any] | None:
        """Search for a book by title and author name.

        Args:
            title: Book title
            author: Author name

        Returns:
            Wikidata entity data or None if not found

        Raises:
            APIError: If API request fails
        """
        self.rate_limiter.wait_if_needed()

        # SPARQL query to find book by title and author
        query = """
        SELECT ?book ?bookLabel ?authorLabel WHERE {{
          ?book wdt:P31 wd:Q7725634 .  # instance of: literary work
          ?book rdfs:label ?title .
          ?book wdt:P50 ?author .  # author property
          ?author rdfs:label ?authorName .

          FILTER(CONTAINS(LCASE(?title), LCASE("{title}")))
          FILTER(CONTAINS(LCASE(?authorName), LCASE("{author}")))
          FILTER(LANG(?title) = "en")
          FILTER(LANG(?authorName) = "en")

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 1
        """.format(title=title.replace('"', '\\"'), author=author.replace('"', '\\"'))

        try:
            logger.debug(f"Searching Wikidata for '{title}' by {author}")
            response = self.session.get(
                self.SPARQL_ENDPOINT, params={"query": query, "format": "json"}, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            if not bindings:
                logger.debug(f"No Wikidata results for '{title}' by {author}")
                return None

            book_uri = bindings[0].get("book", {}).get("value", "")
            if not book_uri:
                return None

            wikidata_id = book_uri.split("/")[-1]
            logger.debug(f"Found Wikidata entity: {wikidata_id}")

            return self._get_entity_data(wikidata_id)

        except requests.exceptions.Timeout as e:
            raise APIError(f"Wikidata API timeout for '{title}'") from e
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response and e.response.status_code == 429:
                raise RateLimitError("Wikidata rate limit exceeded") from e
            raise APIError(f"Wikidata API error: {e}") from e

    def search_author(self, name: str) -> dict[str, Any] | None:
        """Search for an author by name.

        Args:
            name: Author name (full name preferred)

        Returns:
            Wikidata entity data or None if not found

        Raises:
            APIError: If API request fails
        """
        self.rate_limiter.wait_if_needed()

        # SPARQL query to find author
        query = """
        SELECT ?author ?authorLabel ?birthDate ?deathDate ?birthPlace ?deathPlace WHERE {{
          ?author wdt:P31 wd:Q5 .  # instance of: human
          ?author wdt:P106 wd:Q36180 .  # occupation: writer
          ?author rdfs:label ?name .

          FILTER(CONTAINS(LCASE(?name), LCASE("{name}")))
          FILTER(LANG(?name) = "en")

          OPTIONAL {{ ?author wdt:P569 ?birthDate }}
          OPTIONAL {{ ?author wdt:P570 ?deathDate }}
          OPTIONAL {{ ?author wdt:P19 ?birthPlace }}
          OPTIONAL {{ ?author wdt:P20 ?deathPlace }}

          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 1
        """.format(name=name.replace('"', '\\"'))

        try:
            logger.debug(f"Searching Wikidata for author '{name}'")
            response = self.session.get(
                self.SPARQL_ENDPOINT, params={"query": query, "format": "json"}, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            if not bindings:
                logger.debug(f"No Wikidata results for author '{name}'")
                return None

            author_uri = bindings[0].get("author", {}).get("value", "")
            if not author_uri:
                return None

            wikidata_id = author_uri.split("/")[-1]
            logger.debug(f"Found Wikidata entity: {wikidata_id}")

            return self._get_entity_data(wikidata_id)

        except requests.exceptions.Timeout as e:
            raise APIError(f"Wikidata API timeout for author '{name}'") from e
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response and e.response.status_code == 429:
                raise RateLimitError("Wikidata rate limit exceeded") from e
            raise APIError(f"Wikidata API error: {e}") from e

    def _get_entity_data(self, wikidata_id: str) -> dict[str, Any] | None:
        """Fetch full entity data from Wikidata.

        Args:
            wikidata_id: Wikidata Q-number (e.g., 'Q1234')

        Returns:
            Full entity data dictionary or None if fetch fails
        """
        try:
            url = self.ENTITY_URL.format(wikidata_id)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            entities = data.get("entities", {})
            entity_data = entities.get(wikidata_id)

            if not entity_data:
                logger.warning(f"No entity data for {wikidata_id}")
                return None

            return entity_data

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch entity data for {wikidata_id}: {e}")
            return None

    def get_author_influences(self, wikidata_id: str) -> list[dict[str, Any]]:
        """Get authors who influenced or were influenced by this author.

        Args:
            wikidata_id: Author's Wikidata Q-number

        Returns:
            List of influence relationships with influencer/influenced entities
        """
        self.rate_limiter.wait_if_needed()

        query = f"""
        SELECT ?influencer ?influencerLabel ?influenced ?influencedLabel WHERE {{
          {{
            wd:{wikidata_id} wdt:P737 ?influencer .  # influenced by
            BIND(wd:{wikidata_id} AS ?influenced)
          }} UNION {{
            ?influenced wdt:P737 wd:{wikidata_id} .  # this author influenced others
            BIND(wd:{wikidata_id} AS ?influencer)
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """

        try:
            response = self.session.get(
                self.SPARQL_ENDPOINT, params={"query": query, "format": "json"}, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            influences = []
            for binding in bindings:
                influencer_uri = binding.get("influencer", {}).get("value", "")
                influenced_uri = binding.get("influenced", {}).get("value", "")

                if influencer_uri and influenced_uri:
                    influences.append(
                        {
                            "influencer_id": influencer_uri.split("/")[-1],
                            "influencer_name": binding.get("influencerLabel", {}).get("value"),
                            "influenced_id": influenced_uri.split("/")[-1],
                            "influenced_name": binding.get("influencedLabel", {}).get("value"),
                        }
                    )

            logger.debug(f"Found {len(influences)} influence relationships for {wikidata_id}")
            return influences

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch influences for {wikidata_id}: {e}")
            return []

    def get_literary_movements(self, entity_id: str) -> list[dict[str, str]]:
        """Get literary movements associated with a book or author.

        Args:
            entity_id: Wikidata Q-number for book or author

        Returns:
            List of literary movement dictionaries with id and name
        """
        self.rate_limiter.wait_if_needed()

        query = f"""
        SELECT DISTINCT ?movement ?movementLabel WHERE {{
          wd:{entity_id} wdt:P135 ?movement .  # movement property
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """

        try:
            response = self.session.get(
                self.SPARQL_ENDPOINT, params={"query": query, "format": "json"}, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            movements = []
            for binding in bindings:
                movement_uri = binding.get("movement", {}).get("value", "")
                if movement_uri:
                    movements.append(
                        {
                            "id": movement_uri.split("/")[-1],
                            "name": binding.get("movementLabel", {}).get("value", ""),
                        }
                    )

            logger.debug(f"Found {len(movements)} literary movements for {entity_id}")
            return movements

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch literary movements for {entity_id}: {e}")
            return []

    def search_book(self, title: str, author: str) -> dict[str, Any] | None:
        """Search for a book by title and author (implements APIClient interface).

        This is an alias for search_book_by_title_author to satisfy the APIClient interface.

        Args:
            title: Book title
            author: Author name

        Returns:
            Wikidata entity data or None if not found

        Raises:
            APIError: If API request fails
        """
        return self.search_book_by_title_author(title, author)

    def get_rate_limit(self) -> tuple[int, int]:
        """Get rate limit configuration.

        Returns:
            Tuple of (60, 60) - 60 requests per 60 seconds
        """
        return (self.rate_limiter.requests_per_period, self.rate_limiter.period_seconds)

    def close(self) -> None:
        """Close the HTTP session and label resolver."""
        self.session.close()
        self.label_resolver.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
