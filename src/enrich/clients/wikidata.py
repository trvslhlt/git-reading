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

    # API Endpoints
    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
    SEARCH_API = "https://www.wikidata.org/w/api.php"

    # Configuration constants
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 2  # seconds - base delay for exponential backoff
    SPARQL_TIMEOUT = 60  # seconds
    SEARCH_API_TIMEOUT = 30  # seconds
    ENTITY_FETCH_TIMEOUT = 30  # seconds
    SEARCH_RESULT_LIMIT = 10  # number of search results to check

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

        # Simplified SPARQL query for better performance
        query = """
        SELECT ?book WHERE {{
          ?book wdt:P31 wd:Q7725634 ;  # instance of: literary work
                wdt:P50 ?author ;  # author property
                rdfs:label ?title .
          ?author rdfs:label ?authorName .

          FILTER(CONTAINS(LCASE(?title), LCASE("{title}")))
          FILTER(CONTAINS(LCASE(?authorName), LCASE("{author}")))
          FILTER(LANG(?title) = "en")
          FILTER(LANG(?authorName) = "en")
        }}
        LIMIT 1
        """.format(title=title.replace('"', '\\"'), author=author.replace('"', '\\"'))

        # Retry logic with exponential backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(
                    f"Searching Wikidata for '{title}' by {author} (attempt {attempt + 1}/{self.MAX_RETRIES})"
                )
                response = self.session.get(
                    self.SPARQL_ENDPOINT,
                    params={"query": query, "format": "json"},
                    timeout=self.SPARQL_TIMEOUT,
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

            except requests.exceptions.Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        f"Timeout searching for '{title}', retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    import time

                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(
                        f"Wikidata timeout for '{title}' after {self.MAX_RETRIES} attempts"
                    )
                    return None
            except requests.exceptions.RequestException as e:
                if hasattr(e, "response") and e.response and e.response.status_code == 429:
                    raise RateLimitError("Wikidata rate limit exceeded") from e
                logger.warning(f"Wikidata API error for '{title}': {e}")
                return None

        return None

    def search_author(self, name: str) -> dict[str, Any] | None:
        """Search for an author by name.

        Strategy: Try Search API first (faster, more reliable), fall back to SPARQL if needed.

        Args:
            name: Author name (full name preferred)

        Returns:
            Wikidata entity data or None if not found

        Raises:
            APIError: If API request fails
        """
        # Try Search API first (faster and more reliable)
        result = self._search_author_via_api(name)
        if result:
            return result

        # Fall back to SPARQL if Search API didn't find a match
        logger.info(f"Search API didn't find '{name}', trying SPARQL as fallback")
        return self._search_author_via_sparql(name)

    def _search_author_via_sparql(self, name: str) -> dict[str, Any] | None:
        """Search for an author using SPARQL (fallback when Search API fails).

        Args:
            name: Author name

        Returns:
            Wikidata entity data or None if not found
        """
        self.rate_limiter.wait_if_needed()

        # Simplified SPARQL query for better performance
        query = """
        SELECT ?author WHERE {{
          ?author wdt:P31 wd:Q5 ;  # instance of: human
                  wdt:P106 wd:Q36180 ;  # occupation: writer
                  rdfs:label ?name .
          FILTER(CONTAINS(LCASE(?name), LCASE("{name}")))
          FILTER(LANG(?name) = "en")
        }}
        LIMIT 1
        """.format(name=name.replace('"', '\\"'))

        # Retry logic with exponential backoff for timeouts
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.debug(
                    f"Searching Wikidata via SPARQL for '{name}' (attempt {attempt + 1}/{self.MAX_RETRIES})"
                )
                response = self.session.get(
                    self.SPARQL_ENDPOINT,
                    params={"query": query, "format": "json"},
                    timeout=self.SPARQL_TIMEOUT,
                )
                response.raise_for_status()

                data = response.json()
                bindings = data.get("results", {}).get("bindings", [])

                if not bindings:
                    logger.debug(f"No SPARQL results for author '{name}'")
                    return None

                author_uri = bindings[0].get("author", {}).get("value", "")
                if not author_uri:
                    return None

                wikidata_id = author_uri.split("/")[-1]
                logger.debug(f"Found Wikidata entity via SPARQL: {wikidata_id}")

                return self._get_entity_data(wikidata_id)

            except requests.exceptions.Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_BASE_DELAY * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"SPARQL timeout searching for '{name}', retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    import time

                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(
                        f"Wikidata SPARQL timeout for author '{name}' after {self.MAX_RETRIES} attempts"
                    )
                    return None
            except requests.exceptions.RequestException as e:
                if hasattr(e, "response") and e.response and e.response.status_code == 429:
                    raise RateLimitError("Wikidata rate limit exceeded") from e
                logger.warning(f"Wikidata SPARQL error for author '{name}': {e}")
                return None

        return None

    def _search_author_via_api(self, name: str) -> dict[str, Any] | None:
        """Search for an author using Wikidata Search API (primary method).

        This method is faster and more reliable than SPARQL but requires filtering results.

        Args:
            name: Author name

        Returns:
            Wikidata entity data or None if not found
        """
        self.rate_limiter.wait_if_needed()

        try:
            logger.debug(f"Searching Wikidata via Search API for author '{name}'")

            # Use Wikidata Search API
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "language": "en",
                "type": "item",
                "search": name,
                "limit": self.SEARCH_RESULT_LIMIT,
            }

            response = self.session.get(
                self.SEARCH_API, params=params, timeout=self.SEARCH_API_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            search_results = data.get("search", [])

            if not search_results:
                logger.debug(f"No Search API results for author '{name}'")
                return None

            # Filter results to find writers
            # Check each result's entity data to see if they're a writer
            for result in search_results:
                wikidata_id = result.get("id")
                if not wikidata_id:
                    continue

                # Fetch full entity data
                entity_data = self._get_entity_data(wikidata_id)
                if not entity_data:
                    continue

                # Check if this entity is a human who is a writer
                claims = entity_data.get("claims", {})

                # Check instance of (P31) = human (Q5)
                instance_of = claims.get("P31", [])
                is_human = any(
                    claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                    == "Q5"
                    for claim in instance_of
                )

                if not is_human:
                    continue

                # Check occupation (P106) includes writer (Q36180) or related
                occupations = claims.get("P106", [])
                writer_qids = {
                    "Q36180",  # writer
                    "Q6625963",  # novelist
                    "Q49757",  # poet
                    "Q214917",  # playwright
                    "Q4853732",  # essayist
                    "Q3579035",  # screenwriter
                }

                is_writer = any(
                    claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                    in writer_qids
                    for claim in occupations
                )

                if is_writer:
                    logger.debug(f"Found author via Search API: {wikidata_id}")
                    return entity_data

            logger.debug(f"No writer found in Search API results for '{name}'")
            return None

        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response and e.response.status_code == 429:
                raise RateLimitError("Wikidata rate limit exceeded") from e
            logger.warning(f"Wikidata Search API error for author '{name}': {e}")
            return None

    def _get_entity_data(self, wikidata_id: str) -> dict[str, Any] | None:
        """Fetch full entity data from Wikidata.

        Args:
            wikidata_id: Wikidata Q-number (e.g., 'Q1234')

        Returns:
            Full entity data dictionary or None if fetch fails
        """
        try:
            url = self.ENTITY_URL.format(wikidata_id)
            response = self.session.get(url, timeout=self.ENTITY_FETCH_TIMEOUT)
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
