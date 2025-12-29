"""Tests for Wikidata Q-ID label resolution."""

from unittest.mock import Mock, patch

import pytest
import requests

from enrich.clients.wikidata_label_resolver import WikidataLabelResolver


class TestWikidataLabelResolver:
    """Test suite for WikidataLabelResolver."""

    @pytest.fixture
    def resolver(self):
        """Create a WikidataLabelResolver instance."""
        return WikidataLabelResolver()

    @pytest.fixture
    def mock_entity_response(self):
        """Mock response from Wikidata entity API."""
        return {"entities": {"Q84": {"labels": {"en": {"value": "London"}}}}}

    @pytest.fixture
    def mock_batch_response(self):
        """Mock response from Wikidata batch API."""
        return {
            "entities": {
                "Q84": {"labels": {"en": {"value": "London"}}},
                "Q145": {"labels": {"en": {"value": "United Kingdom"}}},
                "Q1860": {"labels": {"en": {"value": "English"}}},
            }
        }

    def test_resolver_initialization(self, resolver):
        """Test resolver initializes with empty cache."""
        assert resolver.cache == {}
        assert resolver.get_cache_size() == 0
        assert resolver.session is not None

    @patch("requests.Session.get")
    def test_resolve_single_qid(self, mock_get, resolver, mock_entity_response):
        """Test resolving a single Q-ID."""
        mock_response = Mock()
        mock_response.json.return_value = mock_entity_response
        mock_get.return_value = mock_response

        label = resolver.resolve("Q84")

        assert label == "London"
        assert resolver.get_cache_size() == 1
        assert "Q84:en" in resolver.cache

    @patch("requests.Session.get")
    def test_resolve_cached_qid(self, mock_get, resolver):
        """Test that cached Q-IDs don't make API calls."""
        # Manually add to cache
        resolver.cache["Q84:en"] = "London"

        label = resolver.resolve("Q84")

        assert label == "London"
        mock_get.assert_not_called()

    @patch("requests.Session.get")
    def test_resolve_batch(self, mock_get, resolver, mock_batch_response):
        """Test batch resolution of multiple Q-IDs."""
        mock_response = Mock()
        mock_response.json.return_value = mock_batch_response
        mock_get.return_value = mock_response

        qids = ["Q84", "Q145", "Q1860"]
        labels = resolver.resolve_batch(qids)

        assert labels == {"Q84": "London", "Q145": "United Kingdom", "Q1860": "English"}
        assert resolver.get_cache_size() == 3

    @patch("requests.Session.get")
    def test_resolve_batch_with_cache(self, mock_get, resolver, mock_batch_response):
        """Test batch resolution with some cached entries."""
        # Pre-cache one entry
        resolver.cache["Q84:en"] = "London"

        mock_response = Mock()
        # Should only fetch Q145 and Q1860
        mock_response.json.return_value = {
            "entities": {
                "Q145": {"labels": {"en": {"value": "United Kingdom"}}},
                "Q1860": {"labels": {"en": {"value": "English"}}},
            }
        }
        mock_get.return_value = mock_response

        qids = ["Q84", "Q145", "Q1860"]
        labels = resolver.resolve_batch(qids)

        assert labels == {"Q84": "London", "Q145": "United Kingdom", "Q1860": "English"}
        # Should have made API call for only 2 uncached IDs
        assert mock_get.call_count == 1

    @patch("requests.Session.get")
    def test_resolve_batch_empty_list(self, mock_get, resolver):
        """Test batch resolution with empty list."""
        labels = resolver.resolve_batch([])

        assert labels == {}
        mock_get.assert_not_called()

    @patch("requests.Session.get")
    def test_resolve_missing_entity(self, mock_get, resolver):
        """Test resolving a Q-ID that doesn't exist."""
        mock_response = Mock()
        mock_response.json.return_value = {"entities": {}}
        mock_get.return_value = mock_response

        label = resolver.resolve("Q99999999")

        assert label is None

    @patch("requests.Session.get")
    def test_resolve_different_language(self, mock_get, resolver):
        """Test resolving Q-ID in different language."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "entities": {"Q84": {"labels": {"fr": {"value": "Londres"}}}}
        }
        mock_get.return_value = mock_response

        label = resolver.resolve("Q84", language="fr")

        assert label == "Londres"
        assert "Q84:fr" in resolver.cache

    def test_clear_cache(self, resolver):
        """Test clearing the cache."""
        resolver.cache["Q84:en"] = "London"
        resolver.cache["Q145:en"] = "United Kingdom"

        assert resolver.get_cache_size() == 2

        resolver.clear_cache()

        assert resolver.get_cache_size() == 0
        assert resolver.cache == {}

    def test_resolve_api_error(self, resolver):
        """Test handling API errors gracefully."""
        # Mock the session's get method to raise a RequestException
        resolver.session.get = Mock(side_effect=requests.exceptions.RequestException("API Error"))

        label = resolver.resolve("Q84")

        assert label is None

    @patch("requests.Session.get")
    def test_resolve_batch_batching(self, mock_get, resolver):
        """Test that batch resolution splits large lists into batches of 50."""
        # Create 75 Q-IDs (should require 2 API calls)
        qids = [f"Q{i}" for i in range(75)]

        mock_response = Mock()
        mock_response.json.return_value = {"entities": {}}
        mock_get.return_value = mock_response

        resolver.resolve_batch(qids)

        # Should have made 2 API calls (50 + 25)
        assert mock_get.call_count == 2

    def test_context_manager(self, resolver):
        """Test using resolver as context manager."""
        with resolver as r:
            assert r is resolver
            assert r.session is not None

        # Session should be closed after context
        # (Can't easily test this without internal access)

    @patch("requests.Session.get")
    def test_batch_with_missing_entities(self, mock_get, resolver):
        """Test batch resolution with some missing entities."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "entities": {
                "Q84": {"labels": {"en": {"value": "London"}}},
                "Q99999": {
                    "missing": ""  # Entity doesn't exist
                },
                "Q145": {"labels": {"en": {"value": "United Kingdom"}}},
            }
        }
        mock_get.return_value = mock_response

        qids = ["Q84", "Q99999", "Q145"]
        labels = resolver.resolve_batch(qids)

        # Should only return labels for existing entities
        assert labels == {"Q84": "London", "Q145": "United Kingdom"}
        # Q99999 should not be in cache
        assert "Q99999:en" not in resolver.cache
