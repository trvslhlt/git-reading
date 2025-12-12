"""Tests for incremental vector store updates.

Tests the update_search_index_incremental function which applies
add/update/delete operations to an existing vector search index.

NOTE: These tests require search dependencies (numpy, faiss, sentence-transformers).
Install with: make search-install or uv pip install -e ".[search]"
"""

import json
import tempfile
from pathlib import Path

import pytest

# Skip entire module if search dependencies not available
pytest.importorskip("numpy")
pytest.importorskip("faiss")
pytest.importorskip("sentence_transformers")

from extract.models import ExtractedItem, ExtractionFile, ExtractionMetadata
from query.search import build_search_index_from_extractions, update_search_index_incremental
from query.vector_store import VectorStore


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as index_dir, tempfile.TemporaryDirectory() as vector_dir:
        yield Path(index_dir), Path(vector_dir)


@pytest.fixture
def model_name():
    """Use a small model for faster testing."""
    return "all-MiniLM-L6-v2"


def create_extraction_file(
    index_dir: Path,
    commit_hash: str,
    extraction_type: str,
    items: list[ExtractedItem],
    previous_commit: str | None = None,
) -> None:
    """Helper to create an extraction file for testing."""
    timestamp = "2024-01-01T12:00:00Z"
    commit_timestamp = "2024-01-01T12:00:00Z"
    filename = f"extraction_20240101_120000_{commit_hash[:7]}.json"

    extraction = ExtractionFile(
        extraction_metadata=ExtractionMetadata(
            timestamp=timestamp,
            git_commit_hash=commit_hash,
            git_commit_timestamp=commit_timestamp,
            extraction_type=extraction_type,
            previous_commit_hash=previous_commit,
            notes_directory="/test/notes",
        ),
        items=items,
    )

    filepath = index_dir / filename
    with open(filepath, "w") as f:
        json.dump(
            {
                "extraction_metadata": {
                    "timestamp": extraction.extraction_metadata.timestamp,
                    "git_commit_hash": extraction.extraction_metadata.git_commit_hash,
                    "git_commit_timestamp": extraction.extraction_metadata.git_commit_timestamp,
                    "extraction_type": extraction.extraction_metadata.extraction_type,
                    "previous_commit_hash": extraction.extraction_metadata.previous_commit_hash,
                    "notes_directory": extraction.extraction_metadata.notes_directory,
                },
                "items": [
                    {
                        "item_id": item.item_id,
                        "operation": item.operation,
                        "book_title": item.book_title,
                        "author_first_name": item.author_first_name,
                        "author_last_name": item.author_last_name,
                        "section": item.section,
                        "content": item.content,
                        "source_file": item.source_file,
                        "date_read": item.date_read,
                    }
                    for item in extraction.items
                ],
            },
            f,
            indent=2,
        )


class TestIncrementalSearchUpdate:
    """Tests for update_search_index_incremental function."""

    def test_add_operation_increases_note_count(self, temp_dirs, model_name):
        """Test that add operations increase the note count in the vector store."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction with 2 notes
        initial_items = [
            ExtractedItem(
                item_id="id1",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="First note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
            ExtractedItem(
                item_id="id2",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Second note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)

        # Build initial index
        build_search_index_from_extractions(index_dir, vector_dir, model_name)

        # Verify initial state
        store = VectorStore.load(vector_dir)
        assert len(store.notes) == 2
        assert len(store.notes) - len(store.deleted_indices) == 2

        # Create incremental extraction with 1 new note
        new_items = [
            ExtractedItem(
                item_id="id3",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Third note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "def456", "incremental", new_items, "abc123")

        # Apply incremental update
        update_search_index_incremental(index_dir, vector_dir)

        # Verify updated state
        store = VectorStore.load(vector_dir)
        assert len(store.notes) == 3
        assert len(store.notes) - len(store.deleted_indices) == 3
        assert store.get_checkpoint() == "def456"

    def test_update_operation_marks_old_deleted_adds_new(self, temp_dirs, model_name):
        """Test that update operations mark old notes as deleted and add new versions."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction
        initial_items = [
            ExtractedItem(
                item_id="id1",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Original content",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)
        build_search_index_from_extractions(index_dir, vector_dir, model_name)

        # Create incremental extraction with update
        update_items = [
            ExtractedItem(
                item_id="id1",
                operation="update",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Updated content",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "def456", "incremental", update_items, "abc123")

        # Apply incremental update
        update_search_index_incremental(index_dir, vector_dir)

        # Verify state
        store = VectorStore.load(vector_dir)
        assert len(store.notes) == 2  # Old + new version
        assert len(store.deleted_indices) == 1  # Old version marked deleted
        assert len(store.notes) - len(store.deleted_indices) == 1  # Only 1 active

        # Verify the active note has updated content
        active_notes = [
            note for i, note in enumerate(store.notes) if i not in store.deleted_indices
        ]
        assert len(active_notes) == 1
        assert active_notes[0].text == "Updated content"

    def test_delete_operation_marks_note_deleted(self, temp_dirs, model_name):
        """Test that delete operations mark notes as deleted."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction
        initial_items = [
            ExtractedItem(
                item_id="id1",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Note to delete",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
            ExtractedItem(
                item_id="id2",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Note to keep",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)
        build_search_index_from_extractions(index_dir, vector_dir, model_name)

        # Create incremental extraction with delete
        delete_items = [
            ExtractedItem(
                item_id="id1",
                operation="delete",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Note to delete",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "def456", "incremental", delete_items, "abc123")

        # Apply incremental update
        update_search_index_incremental(index_dir, vector_dir)

        # Verify state
        store = VectorStore.load(vector_dir)
        assert len(store.notes) == 2  # Both notes still in list
        assert len(store.deleted_indices) == 1  # One marked deleted
        assert len(store.notes) - len(store.deleted_indices) == 1  # One active

    def test_checkpoint_updated_after_each_extraction(self, temp_dirs, model_name):
        """Test that checkpoint is updated after processing each extraction."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction
        initial_items = [
            ExtractedItem(
                item_id="id1",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="First note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)
        build_search_index_from_extractions(index_dir, vector_dir, model_name)

        # Verify initial checkpoint
        store = VectorStore.load(vector_dir)
        assert store.get_checkpoint() == "abc123"

        # Create first incremental extraction
        new_items_1 = [
            ExtractedItem(
                item_id="id2",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Second note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "def456", "incremental", new_items_1, "abc123")

        # Apply first update
        update_search_index_incremental(index_dir, vector_dir)
        store = VectorStore.load(vector_dir)
        assert store.get_checkpoint() == "def456"

        # Create second incremental extraction
        new_items_2 = [
            ExtractedItem(
                item_id="id3",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Third note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "ghi789", "incremental", new_items_2, "def456")

        # Apply second update
        update_search_index_incremental(index_dir, vector_dir)
        store = VectorStore.load(vector_dir)
        assert store.get_checkpoint() == "ghi789"

    def test_mixed_operations_in_single_extraction(self, temp_dirs, model_name):
        """Test that a single extraction can contain add, update, and delete operations."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction with 3 notes
        initial_items = [
            ExtractedItem(
                item_id="id1",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Note to update",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
            ExtractedItem(
                item_id="id2",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Note to delete",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
            ExtractedItem(
                item_id="id3",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Note to keep",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)
        build_search_index_from_extractions(index_dir, vector_dir, model_name)

        # Create incremental extraction with mixed operations
        mixed_items = [
            ExtractedItem(
                item_id="id1",
                operation="update",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Updated note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
            ExtractedItem(
                item_id="id2",
                operation="delete",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Note to delete",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
            ExtractedItem(
                item_id="id4",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Brand new note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "def456", "incremental", mixed_items, "abc123")

        # Apply incremental update
        update_search_index_incremental(index_dir, vector_dir)

        # Verify state
        store = VectorStore.load(vector_dir)
        # Total notes: 3 original + 1 new version of id1 + 1 new note = 5
        assert len(store.notes) == 5
        # Deleted: 1 old version of id1 + 1 deleted id2 = 2
        assert len(store.deleted_indices) == 2
        # Active: 5 - 2 = 3
        assert len(store.notes) - len(store.deleted_indices) == 3

    def test_section_filtering_applied_during_incremental_update(self, temp_dirs, model_name):
        """Test that section filtering is respected during incremental updates."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction with filtered sections
        initial_items = [
            ExtractedItem(
                item_id="id1",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="This is a note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)

        # Build with section filtering
        build_search_index_from_extractions(
            index_dir, vector_dir, model_name, sections_to_index=["notes"]
        )

        # Create incremental extraction with mixed sections
        new_items = [
            ExtractedItem(
                item_id="id2",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Another note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
            ExtractedItem(
                item_id="id3",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="excerpts",
                content="This should be filtered",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "def456", "incremental", new_items, "abc123")

        # Apply incremental update with section filter
        update_search_index_incremental(index_dir, vector_dir, sections_to_index=["notes"])

        # Verify only notes section was added
        store = VectorStore.load(vector_dir)
        assert len(store.notes) - len(store.deleted_indices) == 2
        # Check all active notes are from "notes" section
        active_notes = [
            note for i, note in enumerate(store.notes) if i not in store.deleted_indices
        ]
        assert all(note.section == "notes" for note in active_notes)

    def test_no_new_extractions_returns_early(self, temp_dirs, model_name):
        """Test that function returns early when no new extractions exist."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction
        initial_items = [
            ExtractedItem(
                item_id="id1",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="First note",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)
        build_search_index_from_extractions(index_dir, vector_dir, model_name)

        # Get initial checkpoint
        store = VectorStore.load(vector_dir)
        initial_checkpoint = store.get_checkpoint()
        initial_note_count = len(store.notes)

        # Apply incremental update with no new extractions
        update_search_index_incremental(index_dir, vector_dir)

        # Verify nothing changed
        store = VectorStore.load(vector_dir)
        assert store.get_checkpoint() == initial_checkpoint
        assert len(store.notes) == initial_note_count

    def test_item_id_tracking_across_operations(self, temp_dirs, model_name):
        """Test that item_id properly tracks notes across add/update/delete operations."""
        index_dir, vector_dir = temp_dirs

        # Create initial extraction
        initial_items = [
            ExtractedItem(
                item_id="stable_id",
                operation="add",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Original content",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "abc123", "full", initial_items)
        build_search_index_from_extractions(index_dir, vector_dir, model_name)

        # Verify item_id is tracked
        store = VectorStore.load(vector_dir)
        assert "stable_id" in store.item_id_to_index
        original_index = store.item_id_to_index["stable_id"]

        # Update the item
        update_items = [
            ExtractedItem(
                item_id="stable_id",
                operation="update",
                book_title="Book One",
                author_first_name="John",
                author_last_name="Doe",
                section="notes",
                content="Updated content",
                source_file="doe__john.md",
                date_read="2024-01-01",
            ),
        ]
        create_extraction_file(index_dir, "def456", "incremental", update_items, "abc123")
        update_search_index_incremental(index_dir, vector_dir)

        # Verify item_id points to new version and old is deleted
        store = VectorStore.load(vector_dir)
        assert "stable_id" in store.item_id_to_index
        new_index = store.item_id_to_index["stable_id"]
        assert new_index != original_index  # Different index
        assert original_index in store.deleted_indices  # Old version deleted
        assert new_index not in store.deleted_indices  # New version active
