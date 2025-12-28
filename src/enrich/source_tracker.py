"""Utilities for tracking data provenance and enrichment history."""

from typing import Any

from load.db import DatabaseAdapter


class SourceTracker:
    """Track where enrichment data came from and how it was obtained.

    This class provides utilities for logging enrichment operations to the
    enrichment_log table, enabling complete audit trails and provenance tracking.
    """

    def __init__(self, adapter: DatabaseAdapter):
        """Initialize source tracker.

        Args:
            adapter: Database adapter instance
        """
        self.adapter = adapter

    def log_enrichment(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        new_value: Any,
        source: str,
        method: str,
        old_value: Any = None,
        confidence: float | None = None,
        enriched_by: str | None = None,
        api_endpoint: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Log an enrichment operation to the database.

        Args:
            entity_type: Type of entity ('book', 'author')
            entity_id: ID of the entity being enriched
            field_name: Name of the field being enriched
            new_value: New value being set
            source: Source of the data ('openlibrary', 'wikidata', 'manual', 'llm')
            method: Method used ('api', 'manual_entry', 'llm_generated')
            old_value: Previous value (if any)
            confidence: Confidence score (0.0-1.0) for LLM-generated data
            enriched_by: User identifier for manual entries
            api_endpoint: Specific API endpoint used
            notes: Additional context or notes

        Example:
            >>> tracker.log_enrichment(
            ...     entity_type='book',
            ...     entity_id='some-book-id',
            ...     field_name='isbn_13',
            ...     new_value='9780123456789',
            ...     source='openlibrary',
            ...     method='api',
            ...     api_endpoint='https://openlibrary.org/search.json'
            ... )
        """
        self.adapter.execute(
            """
            INSERT INTO enrichment_log
            (entity_type, entity_id, field_name, old_value, new_value,
             source, method, api_endpoint, confidence, enriched_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity_type,
                entity_id,
                field_name,
                self._serialize_value(old_value),
                self._serialize_value(new_value),
                source,
                method,
                api_endpoint,
                confidence,
                enriched_by,
                notes,
            ),
        )

    def get_field_history(
        self, entity_type: str, entity_id: str, field_name: str
    ) -> list[dict[str, Any]]:
        """Get enrichment history for a specific field.

        Args:
            entity_type: Type of entity ('book', 'author')
            entity_id: ID of the entity
            field_name: Name of the field

        Returns:
            List of enrichment log entries, ordered by most recent first

        Example:
            >>> history = tracker.get_field_history('book', 'book-123', 'isbn_13')
            >>> for entry in history:
            ...     print(f"{entry['enriched_at']}: {entry['old_value']} -> {entry['new_value']}")
        """
        return self.adapter.fetchall(
            """
            SELECT * FROM enrichment_log
            WHERE entity_type = ? AND entity_id = ? AND field_name = ?
            ORDER BY enriched_at DESC
            """,
            (entity_type, entity_id, field_name),
        )

    def get_entity_history(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        """Get all enrichment history for an entity.

        Args:
            entity_type: Type of entity ('book', 'author')
            entity_id: ID of the entity

        Returns:
            List of all enrichment log entries for this entity

        Example:
            >>> history = tracker.get_entity_history('book', 'book-123')
            >>> print(f"Total enrichments: {len(history)}")
        """
        return self.adapter.fetchall(
            """
            SELECT * FROM enrichment_log
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY enriched_at DESC
            """,
            (entity_type, entity_id),
        )

    def get_recent_enrichments(
        self, limit: int = 100, source: str | None = None
    ) -> list[dict[str, Any]]:
        """Get recent enrichment operations.

        Args:
            limit: Maximum number of entries to return
            source: Optional filter by source ('openlibrary', 'wikidata', etc.)

        Returns:
            List of recent enrichment log entries

        Example:
            >>> recent = tracker.get_recent_enrichments(limit=10, source='openlibrary')
        """
        if source:
            return self.adapter.fetchall(
                """
                SELECT * FROM enrichment_log
                WHERE source = ?
                ORDER BY enriched_at DESC
                LIMIT ?
                """,
                (source, limit),
            )
        else:
            return self.adapter.fetchall(
                """
                SELECT * FROM enrichment_log
                ORDER BY enriched_at DESC
                LIMIT ?
                """,
                (limit,),
            )

    def get_enrichment_stats(self) -> dict[str, Any]:
        """Get statistics about enrichment operations.

        Returns:
            Dictionary with enrichment statistics:
                - total_enrichments: Total number of enrichment operations
                - by_source: Count by source
                - by_method: Count by method
                - by_entity_type: Count by entity type

        Example:
            >>> stats = tracker.get_enrichment_stats()
            >>> print(f"Total: {stats['total_enrichments']}")
            >>> print(f"From Open Library: {stats['by_source'].get('openlibrary', 0)}")
        """
        total = self.adapter.fetchscalar("SELECT COUNT(*) FROM enrichment_log")

        # Count by source
        by_source_rows = self.adapter.fetchall(
            """
            SELECT source, COUNT(*) as count
            FROM enrichment_log
            GROUP BY source
            ORDER BY count DESC
            """
        )
        by_source = {row["source"]: row["count"] for row in by_source_rows}

        # Count by method
        by_method_rows = self.adapter.fetchall(
            """
            SELECT method, COUNT(*) as count
            FROM enrichment_log
            GROUP BY method
            ORDER BY count DESC
            """
        )
        by_method = {row["method"]: row["count"] for row in by_method_rows}

        # Count by entity type
        by_entity_rows = self.adapter.fetchall(
            """
            SELECT entity_type, COUNT(*) as count
            FROM enrichment_log
            GROUP BY entity_type
            ORDER BY count DESC
            """
        )
        by_entity_type = {row["entity_type"]: row["count"] for row in by_entity_rows}

        return {
            "total_enrichments": total,
            "by_source": by_source,
            "by_method": by_method,
            "by_entity_type": by_entity_type,
        }

    def _serialize_value(self, value: Any) -> str | None:
        """Convert value to string for storage.

        Args:
            value: Value to serialize

        Returns:
            String representation or None
        """
        if value is None:
            return None
        if isinstance(value, list | dict):
            import json

            return json.dumps(value)
        return str(value)
