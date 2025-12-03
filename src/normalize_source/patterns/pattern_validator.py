"""Validate files using learned patterns."""

from pathlib import Path

from ..models import Issue, IssueSeverity, Pattern
from .pattern_store import PatternStore


class PatternValidator:
    """Validate files using learned patterns."""

    def __init__(self, pattern_store: PatternStore):
        """Initialize the pattern validator.

        Args:
            pattern_store: Store containing learned patterns
        """
        self.pattern_store = pattern_store
        self.section_patterns: dict[str, Pattern] = {
            p.value.lower(): p for p in pattern_store.get_patterns("section_name")
        }

    def validate(self, lines: list[str], file_path: Path) -> list[Issue]:
        """Validate using learned patterns.

        Args:
            lines: List of lines from the markdown file
            file_path: Path to the file being validated

        Returns:
            List of validation issues found
        """
        issues = []

        for line_num, line in enumerate(lines, start=1):
            if line.startswith("## "):
                section_name = line[3:].strip()
                section_lower = section_name.lower()

                # Check against learned patterns
                if section_lower in self.section_patterns:
                    pattern = self.section_patterns[section_lower]

                    # Check if capitalization matches learned pattern
                    if section_name != pattern.value:
                        issues.append(
                            Issue(
                                file_path=file_path,
                                line_number=line_num,
                                severity=IssueSeverity.WARNING,
                                rule_id="PATTERN_001",
                                message=f"Section capitalization differs from learned pattern. Expected: '{pattern.value}', Found: '{section_name}'",
                                context=line.strip(),
                                suggestion=f"## {pattern.value}",
                            )
                        )
                else:
                    # Section not in learned patterns
                    issues.append(
                        Issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=IssueSeverity.INFO,
                            rule_id="PATTERN_002",
                            message=f"Section name '{section_name}' not found in learned patterns",
                            context=line.strip(),
                            suggestion=None,
                        )
                    )

        return issues
