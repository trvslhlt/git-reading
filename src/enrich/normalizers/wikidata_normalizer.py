"""Wikidata entity normalizer for author and book enrichment."""

from typing import Any

from .base import Normalizer


class WikidataBookNormalizer(Normalizer):
    """Normalize Wikidata book entity data to database schema format."""

    def normalize(self, api_response: dict[str, Any], source: str) -> dict[str, Any]:
        """Convert Wikidata entity response to database schema format.

        Args:
            api_response: Raw Wikidata entity data
            source: Should be 'wikidata'

        Returns:
            Normalized dictionary with keys matching database columns:
                - wikidata_id: Wikidata Q-number
                - isbn_10: ISBN-10 identifier
                - isbn_13: ISBN-13 identifier
                - publication_year: Year of publication
                - language: Language code
                - description: Book description
                - subjects: List of subject/genre strings
                - literary_movements: List of movement names
                - awards: List of award names

        Raises:
            ValueError: If API response is malformed
        """
        if source != "wikidata":
            raise ValueError(
                f"WikidataBookNormalizer only handles 'wikidata' source, got '{source}'"
            )

        # Extract Wikidata ID
        wikidata_id = api_response.get("id")

        # Extract claims (statements)
        claims = api_response.get("claims", {})

        # Extract ISBNs
        isbn_10 = self._extract_first_value(claims.get("P957", []))  # ISBN-10
        isbn_13 = self._extract_first_value(claims.get("P212", []))  # ISBN-13

        # Extract publication date
        publication_year = self._extract_year_from_claims(
            claims.get("P577", [])
        )  # publication date

        # Extract language
        language = self._extract_language(claims.get("P407", []))

        # Extract description
        descriptions = api_response.get("descriptions", {})
        description = descriptions.get("en", {}).get("value")

        # Extract genres/subjects
        genres = self._extract_labels(claims.get("P136", []))  # genre
        subjects = self._extract_labels(claims.get("P921", []))  # main subject

        # Combine genres and subjects
        all_subjects = list(set(genres + subjects))

        # Extract literary movements
        literary_movements = self._extract_labels(claims.get("P135", []))  # movement

        # Extract awards
        awards = self._extract_labels(claims.get("P166", []))  # award received

        return {
            "wikidata_id": wikidata_id,
            "isbn_10": isbn_10,
            "isbn_13": isbn_13,
            "publication_year": publication_year,
            "language": language,
            "description": description,
            "subjects": all_subjects,
            "literary_movements": literary_movements,
            "awards": awards,
        }

    def _extract_first_value(self, claims: list[dict[str, Any]]) -> str | None:
        """Extract first string value from Wikidata claims.

        Args:
            claims: List of Wikidata claim objects

        Returns:
            First string value or None
        """
        if not claims:
            return None

        mainsnak = claims[0].get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        return datavalue.get("value")

    def _extract_year_from_claims(self, claims: list[dict[str, Any]]) -> int | None:
        """Extract year from Wikidata time claims.

        Args:
            claims: List of Wikidata claim objects with time values

        Returns:
            Year as integer or None
        """
        if not claims:
            return None

        mainsnak = claims[0].get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value", {})

        # Wikidata time format: "+1984-01-01T00:00:00Z"
        time_str = value.get("time", "")
        if time_str:
            # Extract year from time string
            year_str = time_str.lstrip("+").split("-")[0]
            try:
                return int(year_str)
            except ValueError:
                pass

        return None

    def _extract_language(self, claims: list[dict[str, Any]]) -> str | None:
        """Extract language code from Wikidata claims.

        Args:
            claims: List of Wikidata claim objects

        Returns:
            Language code or None
        """
        if not claims:
            return None

        mainsnak = claims[0].get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value", {})

        # Extract Q-number for language entity
        language_id = value.get("id")

        # Map common language Q-numbers to codes
        # TODO: This should ideally query Wikidata for the language code
        language_map = {
            "Q1860": "en",  # English
            "Q150": "fr",  # French
            "Q188": "de",  # German
            "Q1321": "es",  # Spanish
            "Q652": "it",  # Italian
            "Q7737": "ru",  # Russian
            "Q9056": "cs",  # Czech
            "Q7411": "nl",  # Dutch
            "Q5146": "pt",  # Portuguese
        }

        return language_map.get(language_id)

    def _extract_labels(self, claims: list[dict[str, Any]]) -> list[str]:
        """Extract labels from Wikidata entity references.

        Args:
            claims: List of Wikidata claim objects referencing other entities

        Returns:
            List of entity labels (names)
        """
        labels = []

        for claim in claims:
            mainsnak = claim.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            value = datavalue.get("value", {})

            # For entity references, we have id but not label in raw claims
            # We'd need to either:
            # 1. Fetch entity data separately
            # 2. Use SPARQL to get labels
            # 3. Store Q-numbers and resolve later
            # For now, store the Q-number
            entity_id = value.get("id")
            if entity_id:
                # Check if there's a label in qualifiers or references
                # This is a simplified version - full implementation would fetch labels
                labels.append(entity_id)

        return labels


class WikidataAuthorNormalizer(Normalizer):
    """Normalize Wikidata author entity data to database schema format."""

    def normalize(self, api_response: dict[str, Any], source: str) -> dict[str, Any]:
        """Convert Wikidata author entity to database schema format.

        Args:
            api_response: Raw Wikidata entity data
            source: Should be 'wikidata'

        Returns:
            Normalized dictionary with keys matching database columns:
                - wikidata_id: Wikidata Q-number
                - birth_year: Year of birth
                - death_year: Year of death
                - birth_place: Place of birth
                - death_place: Place of death
                - nationality: Nationality/citizenship
                - bio: Short biography
                - wikipedia_url: English Wikipedia URL
                - viaf_id: VIAF identifier
                - literary_movements: List of movement names
                - influences: List of dicts with influencer/influenced relationships

        Raises:
            ValueError: If API response is malformed
        """
        if source != "wikidata":
            raise ValueError(
                f"WikidataAuthorNormalizer only handles 'wikidata' source, got '{source}'"
            )

        # Extract Wikidata ID
        wikidata_id = api_response.get("id")

        # Extract claims
        claims = api_response.get("claims", {})

        # Extract birth/death dates
        birth_year = self._extract_year_from_claims(claims.get("P569", []))  # date of birth
        death_year = self._extract_year_from_claims(claims.get("P570", []))  # date of death

        # Extract birth/death places (labels)
        birth_place = self._extract_place_label(claims.get("P19", []))  # place of birth
        death_place = self._extract_place_label(claims.get("P20", []))  # place of death

        # Extract nationality/citizenship
        nationality = self._extract_place_label(claims.get("P27", []))  # country of citizenship

        # Extract bio from description
        descriptions = api_response.get("descriptions", {})
        bio = descriptions.get("en", {}).get("value")

        # Extract Wikipedia URL
        sitelinks = api_response.get("sitelinks", {})
        enwiki = sitelinks.get("enwiki", {})
        wikipedia_title = enwiki.get("title")
        wikipedia_url = (
            f"https://en.wikipedia.org/wiki/{wikipedia_title.replace(' ', '_')}"
            if wikipedia_title
            else None
        )

        # Extract VIAF ID
        viaf_id = self._extract_first_value(claims.get("P214", []))  # VIAF ID

        # Extract literary movements
        literary_movements = self._extract_labels(claims.get("P135", []))  # movement

        return {
            "wikidata_id": wikidata_id,
            "birth_year": birth_year,
            "death_year": death_year,
            "birth_place": birth_place,
            "death_place": death_place,
            "nationality": nationality,
            "bio": bio,
            "wikipedia_url": wikipedia_url,
            "viaf_id": viaf_id,
            "literary_movements": literary_movements,
        }

    def _extract_first_value(self, claims: list[dict[str, Any]]) -> str | None:
        """Extract first string value from Wikidata claims."""
        if not claims:
            return None

        mainsnak = claims[0].get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        return datavalue.get("value")

    def _extract_year_from_claims(self, claims: list[dict[str, Any]]) -> int | None:
        """Extract year from Wikidata time claims."""
        if not claims:
            return None

        mainsnak = claims[0].get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value", {})

        time_str = value.get("time", "")
        if time_str:
            year_str = time_str.lstrip("+").split("-")[0]
            try:
                return int(year_str)
            except ValueError:
                pass

        return None

    def _extract_place_label(self, claims: list[dict[str, Any]]) -> str | None:
        """Extract place label from Wikidata claims.

        Note: This returns the Q-number. Full implementation would fetch the label.
        """
        if not claims:
            return None

        mainsnak = claims[0].get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value", {})

        return value.get("id")  # Returns Q-number for now

    def _extract_labels(self, claims: list[dict[str, Any]]) -> list[str]:
        """Extract labels from Wikidata entity references.

        Note: This returns Q-numbers. Full implementation would fetch labels.
        """
        labels = []

        for claim in claims:
            mainsnak = claim.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            value = datavalue.get("value", {})

            entity_id = value.get("id")
            if entity_id:
                labels.append(entity_id)

        return labels
