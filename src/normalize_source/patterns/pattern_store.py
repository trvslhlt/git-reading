"""Storage for learned patterns."""

import json
from pathlib import Path

from ..models import Pattern


class PatternStore:
    """Storage for learned patterns."""

    def __init__(self):
        """Initialize an empty pattern store."""
        self.patterns: dict[str, list[Pattern]] = {}

    def add_pattern(self, pattern: Pattern):
        """Add a pattern to the store.

        Args:
            pattern: Pattern to add
        """
        if pattern.pattern_type not in self.patterns:
            self.patterns[pattern.pattern_type] = []
        self.patterns[pattern.pattern_type].append(pattern)

    def get_patterns(self, pattern_type: str) -> list[Pattern]:
        """Get all patterns of a specific type.

        Args:
            pattern_type: Type of patterns to retrieve

        Returns:
            List of patterns matching the type
        """
        return self.patterns.get(pattern_type, [])

    def save(self, file_path: Path):
        """Save patterns to JSON file.

        Args:
            file_path: Path where patterns should be saved
        """
        data = {
            pattern_type: [
                {
                    "value": p.value,
                    "frequency": p.frequency,
                    "confidence": p.confidence,
                    "examples": p.examples,
                }
                for p in patterns
            ]
            for pattern_type, patterns in self.patterns.items()
        }

        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, file_path: Path) -> "PatternStore":
        """Load patterns from JSON file.

        Args:
            file_path: Path to patterns JSON file

        Returns:
            PatternStore loaded from file
        """
        store = cls()
        data = json.loads(file_path.read_text(encoding="utf-8"))

        for pattern_type, pattern_list in data.items():
            for p_data in pattern_list:
                pattern = Pattern(
                    pattern_type=pattern_type,
                    value=p_data["value"],
                    frequency=p_data["frequency"],
                    confidence=p_data["confidence"],
                    examples=p_data["examples"],
                )
                store.add_pattern(pattern)

        return store
