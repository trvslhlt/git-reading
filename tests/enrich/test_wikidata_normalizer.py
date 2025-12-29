"""Tests for Wikidata normalizers."""

import pytest

from enrich.normalizers.wikidata_normalizer import WikidataAuthorNormalizer, WikidataBookNormalizer


class TestWikidataBookNormalizer:
    """Tests for WikidataBookNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance."""
        return WikidataBookNormalizer()

    @pytest.fixture
    def sample_wikidata_book(self):
        """Sample Wikidata book entity response."""
        return {
            "id": "Q123456",
            "claims": {
                "P957": [  # ISBN-10
                    {"mainsnak": {"datavalue": {"value": "0553293354"}}}
                ],
                "P212": [  # ISBN-13
                    {"mainsnak": {"datavalue": {"value": "978-0553293357"}}}
                ],
                "P577": [  # publication date
                    {"mainsnak": {"datavalue": {"value": {"time": "+1984-01-01T00:00:00Z"}}}}
                ],
                "P407": [  # language
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "id": "Q1860"  # English
                                }
                            }
                        }
                    }
                ],
                "P136": [  # genre
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "id": "Q24925"  # Science fiction
                                }
                            }
                        }
                    }
                ],
            },
            "descriptions": {"en": {"value": "Science fiction novel by William Gibson"}},
        }

    def test_normalize_basic_fields(self, normalizer, sample_wikidata_book):
        """Test normalization of basic book fields."""
        result = normalizer.normalize(sample_wikidata_book, "wikidata")

        assert result["wikidata_id"] == "Q123456"
        assert result["isbn_10"] == "0553293354"
        assert result["isbn_13"] == "978-0553293357"
        assert result["publication_year"] == 1984
        assert result["language"] == "en"
        assert result["description"] == "Science fiction novel by William Gibson"

    def test_normalize_subjects(self, normalizer, sample_wikidata_book):
        """Test subject extraction."""
        result = normalizer.normalize(sample_wikidata_book, "wikidata")

        # Subjects are Q-numbers for now (would be resolved to labels in Phase 2.2)
        assert len(result["subjects"]) > 0
        assert isinstance(result["subjects"], list)

    def test_normalize_missing_fields(self, normalizer):
        """Test normalization with missing fields."""
        minimal_book = {
            "id": "Q789",
            "claims": {},
            "descriptions": {},
        }

        result = normalizer.normalize(minimal_book, "wikidata")

        assert result["wikidata_id"] == "Q789"
        assert result["isbn_10"] is None
        assert result["isbn_13"] is None
        assert result["publication_year"] is None
        assert result["description"] is None
        assert result["subjects"] == []

    def test_wrong_source_raises_error(self, normalizer, sample_wikidata_book):
        """Test that wrong source parameter raises error."""
        with pytest.raises(ValueError, match="only handles 'wikidata' source"):
            normalizer.normalize(sample_wikidata_book, "openlibrary")


class TestWikidataAuthorNormalizer:
    """Tests for WikidataAuthorNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create normalizer instance."""
        return WikidataAuthorNormalizer()

    @pytest.fixture
    def sample_wikidata_author(self):
        """Sample Wikidata author entity response."""
        return {
            "id": "Q42",
            "claims": {
                "P569": [  # date of birth
                    {"mainsnak": {"datavalue": {"value": {"time": "+1952-03-11T00:00:00Z"}}}}
                ],
                "P570": [  # date of death
                    {"mainsnak": {"datavalue": {"value": {"time": "+2001-05-11T00:00:00Z"}}}}
                ],
                "P19": [  # place of birth
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "id": "Q84"  # London
                                }
                            }
                        }
                    }
                ],
                "P27": [  # citizenship
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {
                                    "id": "Q145"  # United Kingdom
                                }
                            }
                        }
                    }
                ],
                "P214": [  # VIAF ID
                    {"mainsnak": {"datavalue": {"value": "113230702"}}}
                ],
            },
            "descriptions": {"en": {"value": "English writer and humorist"}},
            "sitelinks": {"enwiki": {"title": "Douglas_Adams"}},
        }

    def test_normalize_basic_fields(self, normalizer, sample_wikidata_author):
        """Test normalization of basic author fields."""
        result = normalizer.normalize(sample_wikidata_author, "wikidata")

        assert result["wikidata_id"] == "Q42"
        assert result["birth_year"] == 1952
        assert result["death_year"] == 2001
        assert result["bio"] == "English writer and humorist"
        assert result["wikipedia_url"] == "https://en.wikipedia.org/wiki/Douglas_Adams"
        assert result["viaf_id"] == "113230702"

    def test_normalize_places(self, normalizer, sample_wikidata_author):
        """Test place normalization."""
        result = normalizer.normalize(sample_wikidata_author, "wikidata")

        # Places are Q-numbers for now (would be resolved in Phase 2.2)
        assert result["birth_place"] == "Q84"
        assert result["nationality"] == "Q145"

    def test_normalize_missing_death(self, normalizer):
        """Test living author (no death date)."""
        living_author = {
            "id": "Q123",
            "claims": {
                "P569": [{"mainsnak": {"datavalue": {"value": {"time": "+1980-01-01T00:00:00Z"}}}}],
            },
            "descriptions": {},
            "sitelinks": {},
        }

        result = normalizer.normalize(living_author, "wikidata")

        assert result["birth_year"] == 1980
        assert result["death_year"] is None

    def test_wrong_source_raises_error(self, normalizer, sample_wikidata_author):
        """Test that wrong source parameter raises error."""
        with pytest.raises(ValueError, match="only handles 'wikidata' source"):
            normalizer.normalize(sample_wikidata_author, "openlibrary")
