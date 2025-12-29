"""Tests for Q-ID resolution in Wikidata normalizers."""

from unittest.mock import Mock

import pytest

from enrich.normalizers.wikidata_normalizer import (
    WikidataAuthorNormalizer,
    WikidataBookNormalizer,
)


class TestBookNormalizerQIDResolution:
    """Test Q-ID resolution in WikidataBookNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create a WikidataBookNormalizer instance."""
        return WikidataBookNormalizer()

    @pytest.fixture
    def mock_label_resolver(self):
        """Create a mock label resolver."""
        resolver = Mock()
        resolver.resolve_batch.return_value = {
            "Q24925": "Science fiction",
            "Q8261": "Novel",
            "Q1234": "Modernism",
        }
        return resolver

    def test_resolve_book_subjects(self, normalizer, mock_label_resolver):
        """Test resolving Q-IDs in book subjects."""
        normalized_data = {
            "wikidata_id": "Q123",
            "subjects": ["Q24925", "Q8261"],
            "literary_movements": [],
        }

        result = WikidataBookNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        assert result["subjects"] == ["Science fiction", "Novel"]
        mock_label_resolver.resolve_batch.assert_called_once()

    def test_resolve_book_movements(self, normalizer, mock_label_resolver):
        """Test resolving Q-IDs in literary movements."""
        normalized_data = {
            "wikidata_id": "Q123",
            "subjects": [],
            "literary_movements": ["Q1234"],
        }

        result = WikidataBookNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        assert result["literary_movements"] == ["Modernism"]

    def test_resolve_mixed_qids_and_strings(self, normalizer, mock_label_resolver):
        """Test resolving data with both Q-IDs and regular strings."""
        normalized_data = {
            "subjects": ["Q24925", "Fiction", "Q8261", "Adventure"],
            "literary_movements": ["Modernism", "Q1234"],
        }

        result = WikidataBookNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        # Should preserve non-Q-ID strings
        assert "Fiction" in result["subjects"]
        assert "Adventure" in result["subjects"]
        assert "Science fiction" in result["subjects"]
        assert "Novel" in result["subjects"]

        assert "Modernism" in result["literary_movements"]

    def test_resolve_empty_lists(self, normalizer, mock_label_resolver):
        """Test resolving with empty subject/movement lists."""
        normalized_data = {
            "subjects": [],
            "literary_movements": [],
        }

        result = WikidataBookNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        assert result["subjects"] == []
        assert result["literary_movements"] == []
        # Should not make API call with no Q-IDs
        mock_label_resolver.resolve_batch.assert_not_called()

    def test_resolve_no_qids(self, normalizer, mock_label_resolver):
        """Test resolving data with no Q-IDs."""
        normalized_data = {
            "subjects": ["Fiction", "Adventure"],
            "literary_movements": ["Modernism"],
        }

        result = WikidataBookNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        # Should preserve all original strings
        assert result["subjects"] == ["Fiction", "Adventure"]
        assert result["literary_movements"] == ["Modernism"]
        # Should not make API call
        mock_label_resolver.resolve_batch.assert_not_called()

    def test_resolve_unresolved_qids(self, normalizer):
        """Test handling Q-IDs that can't be resolved."""
        resolver = Mock()
        # Return partial results
        resolver.resolve_batch.return_value = {
            "Q24925": "Science fiction",
            # Q99999 not resolved
        }

        normalized_data = {
            "subjects": ["Q24925", "Q99999"],
            "literary_movements": [],
        }

        result = WikidataBookNormalizer.resolve_qids(normalized_data, resolver)

        # Should keep Q-ID if resolution fails
        assert "Science fiction" in result["subjects"]
        assert "Q99999" in result["subjects"]


class TestAuthorNormalizerQIDResolution:
    """Test Q-ID resolution in WikidataAuthorNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create a WikidataAuthorNormalizer instance."""
        return WikidataAuthorNormalizer()

    @pytest.fixture
    def mock_label_resolver(self):
        """Create a mock label resolver."""
        resolver = Mock()
        resolver.resolve_batch.return_value = {
            "Q84": "London",
            "Q145": "United Kingdom",
            "Q1234": "Modernism",
        }
        return resolver

    def test_resolve_author_places(self, normalizer, mock_label_resolver):
        """Test resolving Q-IDs in author birth/death places."""
        normalized_data = {
            "wikidata_id": "Q42",
            "birth_place": "Q84",
            "death_place": "Q84",
            "nationality": "Q145",
            "literary_movements": [],
        }

        result = WikidataAuthorNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        assert result["birth_place"] == "London"
        assert result["death_place"] == "London"
        assert result["nationality"] == "United Kingdom"

    def test_resolve_author_movements(self, normalizer, mock_label_resolver):
        """Test resolving Q-IDs in author literary movements."""
        normalized_data = {
            "wikidata_id": "Q42",
            "literary_movements": ["Q1234"],
        }

        result = WikidataAuthorNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        assert result["literary_movements"] == ["Modernism"]

    def test_resolve_missing_fields(self, normalizer, mock_label_resolver):
        """Test resolving when place fields are None."""
        normalized_data = {
            "wikidata_id": "Q42",
            "birth_place": None,
            "death_place": None,
            "nationality": "Q145",
            "literary_movements": [],
        }

        result = WikidataAuthorNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        assert result["birth_place"] is None
        assert result["death_place"] is None
        assert result["nationality"] == "United Kingdom"

    def test_resolve_non_qid_places(self, normalizer, mock_label_resolver):
        """Test handling places that aren't Q-IDs (shouldn't happen but be safe)."""
        normalized_data = {
            "birth_place": "London",  # Already a string, not Q-ID
            "death_place": "Q84",
            "nationality": None,
            "literary_movements": [],
        }

        result = WikidataAuthorNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        # Should preserve non-Q-ID strings
        assert result["birth_place"] == "London"
        assert result["death_place"] == "London"

    def test_resolve_mixed_movements(self, normalizer, mock_label_resolver):
        """Test resolving movements with mixed Q-IDs and strings."""
        normalized_data = {
            "literary_movements": ["Q1234", "Romanticism", "Victorian"],
        }

        result = WikidataAuthorNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        # Should preserve non-Q-ID strings
        assert "Modernism" in result["literary_movements"]
        assert "Romanticism" in result["literary_movements"]
        assert "Victorian" in result["literary_movements"]

    def test_resolve_empty_data(self, normalizer, mock_label_resolver):
        """Test resolving with no Q-IDs to resolve."""
        normalized_data = {
            "birth_place": None,
            "death_place": None,
            "nationality": None,
            "literary_movements": [],
        }

        WikidataAuthorNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        # Should not make API call
        mock_label_resolver.resolve_batch.assert_not_called()

    def test_resolve_batch_call_efficiency(self, normalizer, mock_label_resolver):
        """Test that all Q-IDs are resolved in single batch call."""
        normalized_data = {
            "birth_place": "Q84",
            "death_place": "Q84",
            "nationality": "Q145",
            "literary_movements": ["Q1234"],
        }

        WikidataAuthorNormalizer.resolve_qids(normalized_data, mock_label_resolver)

        # Should make exactly one batch call
        assert mock_label_resolver.resolve_batch.call_count == 1

        # Should have requested all unique Q-IDs
        called_qids = mock_label_resolver.resolve_batch.call_args[0][0]
        assert "Q84" in called_qids
        assert "Q145" in called_qids
        assert "Q1234" in called_qids
