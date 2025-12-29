"""Wikidata Q-ID to label resolution with caching."""

import requests

from common.logger import get_logger

logger = get_logger(__name__)


class WikidataLabelResolver:
    """Resolve Wikidata Q-IDs to human-readable labels.

    This class provides efficient batch resolution of Q-IDs to labels
    with in-memory caching to minimize API calls.
    """

    ENTITY_API = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
    BATCH_API = "https://www.wikidata.org/w/api.php"

    def __init__(self):
        """Initialize label resolver with empty cache."""
        self.cache: dict[str, str] = {}
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "git-reading/1.0 (https://github.com/trvslhlt/git-reading)",
            }
        )

    def resolve(self, qid: str, language: str = "en") -> str | None:
        """Resolve a single Q-ID to its label.

        Args:
            qid: Wikidata Q-ID (e.g., 'Q84')
            language: Language code (default: 'en')

        Returns:
            Label string or None if not found

        Example:
            >>> resolver = WikidataLabelResolver()
            >>> resolver.resolve('Q84')
            'London'
        """
        # Check cache first
        cache_key = f"{qid}:{language}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Fetch from API
        try:
            url = self.ENTITY_API.format(qid)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            entities = data.get("entities", {})
            entity_data = entities.get(qid, {})

            labels = entity_data.get("labels", {})
            label_obj = labels.get(language, {})
            label = label_obj.get("value")

            if label:
                self.cache[cache_key] = label
                return label

            logger.debug(f"No label found for {qid} in language {language}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to resolve label for {qid}: {e}")
            return None

    def resolve_batch(self, qids: list[str], language: str = "en") -> dict[str, str]:
        """Resolve multiple Q-IDs to labels in a single API call.

        Args:
            qids: List of Wikidata Q-IDs
            language: Language code (default: 'en')

        Returns:
            Dictionary mapping Q-IDs to labels

        Example:
            >>> resolver = WikidataLabelResolver()
            >>> resolver.resolve_batch(['Q84', 'Q145'])
            {'Q84': 'London', 'Q145': 'United Kingdom'}
        """
        if not qids:
            return {}

        # Separate cached and uncached IDs
        results = {}
        uncached_qids = []

        for qid in qids:
            cache_key = f"{qid}:{language}"
            if cache_key in self.cache:
                results[qid] = self.cache[cache_key]
            else:
                uncached_qids.append(qid)

        if not uncached_qids:
            return results

        # Fetch uncached IDs (max 50 at a time per Wikidata API limits)
        for i in range(0, len(uncached_qids), 50):
            batch = uncached_qids[i : i + 50]
            batch_results = self._fetch_batch(batch, language)
            results.update(batch_results)

        return results

    def _fetch_batch(self, qids: list[str], language: str) -> dict[str, str]:
        """Fetch labels for a batch of Q-IDs via the Wikidata API.

        Args:
            qids: List of Q-IDs (max 50)
            language: Language code

        Returns:
            Dictionary mapping Q-IDs to labels
        """
        try:
            params = {
                "action": "wbgetentities",
                "ids": "|".join(qids),
                "props": "labels",
                "languages": language,
                "format": "json",
            }

            response = self.session.get(self.BATCH_API, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            entities = data.get("entities", {})

            results = {}
            for qid, entity_data in entities.items():
                if "missing" in entity_data:
                    logger.debug(f"Entity {qid} not found")
                    continue

                labels = entity_data.get("labels", {})
                label_obj = labels.get(language, {})
                label = label_obj.get("value")

                if label:
                    results[qid] = label
                    # Cache the result
                    cache_key = f"{qid}:{language}"
                    self.cache[cache_key] = label

            return results

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch batch labels: {e}")
            return {}

    def clear_cache(self):
        """Clear the label cache."""
        self.cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of cached labels.

        Returns:
            Number of cached Q-ID/label pairs
        """
        return len(self.cache)

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
