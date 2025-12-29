"""Tests for author influence functionality."""

from unittest.mock import Mock, patch

import pytest

from enrich.orchestrator import EnrichmentOrchestrator


class TestAuthorInfluences:
    """Test suite for author influence enrichment."""

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock database adapter."""
        adapter = Mock()
        adapter.fetchone = Mock(return_value=None)
        adapter.fetchall = Mock(return_value=[])
        adapter.execute = Mock()
        adapter.commit = Mock()
        adapter.rollback = Mock()
        adapter.placeholder = "?"
        return adapter

    @pytest.fixture
    def mock_wikidata_client(self):
        """Create a mock Wikidata client."""
        client = Mock()
        client.get_author_influences = Mock(return_value=[])
        client.search_author = Mock(return_value=None)
        client.label_resolver = Mock()
        return client

    @pytest.fixture
    def orchestrator(self, mock_adapter, mock_wikidata_client):
        """Create orchestrator with mocked dependencies."""
        with patch("enrich.orchestrator.OpenLibraryClient"):
            with patch("enrich.orchestrator.WikidataClient", return_value=mock_wikidata_client):
                orch = EnrichmentOrchestrator(mock_adapter, sources=["wikidata"])
                orch.wikidata_client = mock_wikidata_client
                return orch

    def test_get_author_influences_called(self, orchestrator, mock_adapter, mock_wikidata_client):
        """Test that get_author_influences is called during enrichment."""
        # Mock successful author search
        mock_wikidata_client.search_author.return_value = {
            "id": "Q42",
            "claims": {},
            "descriptions": {},
            "sitelinks": {},
        }

        # Mock fetchone to return wikidata_id when queried
        def fetchone_side_effect(query, params=None):
            if "wikidata_id" in query and params and params[0] == "author-123":
                return {"wikidata_id": "Q42"}
            return None

        mock_adapter.fetchone.side_effect = fetchone_side_effect

        # Enrich author
        orchestrator.enrich_author("author-123", "Douglas Adams")

        # Verify get_author_influences was called with the Wikidata ID
        mock_wikidata_client.get_author_influences.assert_called_once_with("Q42")

    def test_add_author_influences_influenced_by(self, orchestrator, mock_adapter):
        """Test adding influence where enriched author was influenced by someone."""

        # Setup: author-123 has wikidata_id Q42
        def fetchone_side_effect(query, params=None):
            if "wikidata_id" in query and "author-123" in str(params):
                return {"wikidata_id": "Q42"}
            # When creating new author (influencer), they don't exist yet
            if "wikidata_id" in query and "Q100" in str(params):
                return None
            return None

        mock_adapter.fetchone.side_effect = fetchone_side_effect

        influences = [
            {
                "influencer_id": "Q100",
                "influencer_name": "Isaac Asimov",
                "influenced_id": "Q42",  # Douglas Adams
                "influenced_name": "Douglas Adams",
            }
        ]

        count = orchestrator._add_author_influences("author-123", influences, "Q42")

        # Verify the influence was added
        assert count == 1

        # Verify execute was called to insert the relationship
        # Should insert with influencer=isaac-asimov, influenced=author-123
        execute_calls = [call[0] for call in mock_adapter.execute.call_args_list]
        insert_calls = [call for call in execute_calls if "author_influences" in str(call[0])]
        assert len(insert_calls) >= 1

    def test_add_author_influences_influenced_others(self, orchestrator, mock_adapter):
        """Test adding influence where enriched author influenced someone else."""

        # Setup: author-123 has wikidata_id Q42
        def fetchone_side_effect(query, params=None):
            if "wikidata_id" in query and "author-123" in str(params):
                return {"wikidata_id": "Q42"}
            # When creating new author (influenced), they don't exist yet
            if "wikidata_id" in query and "Q200" in str(params):
                return None
            return None

        mock_adapter.fetchone.side_effect = fetchone_side_effect

        influences = [
            {
                "influencer_id": "Q42",  # Douglas Adams
                "influencer_name": "Douglas Adams",
                "influenced_id": "Q200",
                "influenced_name": "Terry Pratchett",
            }
        ]

        count = orchestrator._add_author_influences("author-123", influences, "Q42")

        # Verify the influence was added
        assert count == 1

        # Verify execute was called to insert the relationship
        execute_calls = [call[0] for call in mock_adapter.execute.call_args_list]
        insert_calls = [call for call in execute_calls if "author_influences" in str(call[0])]
        assert len(insert_calls) >= 1

    def test_add_author_influences_bidirectional(self, orchestrator, mock_adapter):
        """Test adding both directions (influenced by and influenced others)."""

        # Setup: author-123 has wikidata_id Q42
        def fetchone_side_effect(query, params=None):
            if "wikidata_id" in query and "author-123" in str(params):
                return {"wikidata_id": "Q42"}
            # New authors don't exist yet
            if "wikidata_id" in query and ("Q100" in str(params) or "Q200" in str(params)):
                return None
            return None

        mock_adapter.fetchone.side_effect = fetchone_side_effect

        influences = [
            {
                "influencer_id": "Q100",
                "influencer_name": "Isaac Asimov",
                "influenced_id": "Q42",
                "influenced_name": "Douglas Adams",
            },
            {
                "influencer_id": "Q42",
                "influencer_name": "Douglas Adams",
                "influenced_id": "Q200",
                "influenced_name": "Terry Pratchett",
            },
        ]

        count = orchestrator._add_author_influences("author-123", influences, "Q42")

        # Verify both influences were added
        assert count == 2

    def test_add_author_influences_empty_list(self, orchestrator, mock_adapter):
        """Test handling empty influence list."""
        count = orchestrator._add_author_influences("author-123", [], "Q42")

        # Should return 0
        assert count == 0

        # Should not insert anything
        execute_calls = [call[0] for call in mock_adapter.execute.call_args_list]
        insert_calls = [call for call in execute_calls if "author_influences" in str(call[0])]
        assert len(insert_calls) == 0

    def test_add_author_influences_missing_data(self, orchestrator, mock_adapter):
        """Test handling influence with missing data."""
        # Setup wikidata_id
        mock_adapter.fetchone.return_value = {"wikidata_id": "Q42"}

        influences = [
            {
                "influencer_id": "Q100",
                # Missing influencer_name
                "influenced_id": "Q42",
                "influenced_name": "Douglas Adams",
            }
        ]

        count = orchestrator._add_author_influences("author-123", influences, "Q42")

        # Should skip the incomplete influence
        assert count == 0

    def test_get_or_create_author_from_wikidata_new(self, orchestrator, mock_adapter):
        """Test creating a new author from Wikidata ID and name."""
        # Author doesn't exist yet
        mock_adapter.fetchone.return_value = None

        author_id = orchestrator._get_or_create_author_from_wikidata("Q42", "Douglas Adams")

        # Verify author ID was generated correctly
        assert author_id == "douglas-adams"

        # Verify INSERT was called
        execute_calls = [call[0] for call in mock_adapter.execute.call_args_list]
        insert_calls = [call for call in execute_calls if "INSERT INTO authors" in str(call[0])]
        assert len(insert_calls) == 1

        # Verify the correct values were inserted
        insert_args = mock_adapter.execute.call_args_list[-1][0]
        assert "Q42" in str(insert_args)
        assert "Douglas Adams" in str(insert_args)

    def test_get_or_create_author_from_wikidata_existing(self, orchestrator, mock_adapter):
        """Test getting an existing author by Wikidata ID."""
        # Author already exists
        mock_adapter.fetchone.return_value = {"id": "existing-author-id"}

        author_id = orchestrator._get_or_create_author_from_wikidata("Q42", "Douglas Adams")

        # Should return existing ID
        assert author_id == "existing-author-id"

        # Should not insert
        execute_calls = [call[0] for call in mock_adapter.execute.call_args_list]
        insert_calls = [call for call in execute_calls if "INSERT INTO authors" in str(call[0])]
        assert len(insert_calls) == 0

    def test_get_or_create_author_single_name(self, orchestrator, mock_adapter):
        """Test creating author with single name (no spaces)."""
        mock_adapter.fetchone.return_value = None

        orchestrator._get_or_create_author_from_wikidata("Q100", "Plato")

        # Verify author was created with no first name
        execute_calls = [call[0] for call in mock_adapter.execute.call_args_list]
        insert_calls = [call for call in execute_calls if "INSERT INTO authors" in str(call[0])]
        assert len(insert_calls) == 1

        # Check the INSERT parameters
        insert_call = [
            call
            for call in mock_adapter.execute.call_args_list
            if "INSERT INTO authors" in str(call[0])
        ][0]
        insert_params = insert_call[0][1]
        # Parameters: (id, name, first_name, last_name, wikidata_id)
        assert insert_params[1] == "Plato"  # name
        assert insert_params[2] is None  # first_name
        assert insert_params[3] == "Plato"  # last_name

    def test_get_author_wikidata_id(self, orchestrator, mock_adapter):
        """Test getting Wikidata ID for an author."""
        mock_adapter.fetchone.return_value = {"wikidata_id": "Q42"}

        wikidata_id = orchestrator._get_author_wikidata_id("author-123")

        assert wikidata_id == "Q42"

    def test_get_author_wikidata_id_none(self, orchestrator, mock_adapter):
        """Test getting Wikidata ID when not set."""
        mock_adapter.fetchone.return_value = {"wikidata_id": None}

        wikidata_id = orchestrator._get_author_wikidata_id("author-123")

        assert wikidata_id is None

    def test_get_author_wikidata_id_author_not_found(self, orchestrator, mock_adapter):
        """Test getting Wikidata ID for non-existent author."""
        mock_adapter.fetchone.return_value = None

        wikidata_id = orchestrator._get_author_wikidata_id("nonexistent")

        assert wikidata_id is None
