"""Section name validation rules."""

import difflib
import re
from pathlib import Path

from ..models import Issue, IssueSeverity

# Canonical section names from extract/main.py
CANONICAL_SECTIONS: set[str] = {
    "terms",
    "notes",
    "excerpts",
    "threads",
    "ideas",
    "representations",
    "images",
    "same time",
    "thread",
    "note",
    "excerpt",
    "term",
}


class SectionNameValidator:
    """Validates section header names."""

    RULE_PREFIX = "SECTION"

    def __init__(self, canonical_sections: set[str] = CANONICAL_SECTIONS):
        """Initialize validator with canonical section names.

        Args:
            canonical_sections: Set of valid section names (lowercase)
        """
        self.canonical_sections = canonical_sections
        self.case_normalized = {s.lower(): s for s in canonical_sections}

    def validate(self, lines: list[str], file_path: Path) -> list[Issue]:
        """Validate section header names.

        Args:
            lines: List of lines from the markdown file
            file_path: Path to the file being validated

        Returns:
            List of validation issues found
        """
        issues = []
        section_pattern = re.compile(r"^##\s+(.+)$")

        for line_num, line in enumerate(lines, start=1):
            match = section_pattern.match(line)
            if not match:
                continue

            section_name = match.group(1).strip()
            section_lower = section_name.lower()

            # Check if it's a known section (case-insensitive)
            if section_lower in self.case_normalized:
                canonical = self.case_normalized[section_lower]

                # Check capitalization consistency
                if section_name != canonical:
                    issues.append(
                        Issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=IssueSeverity.WARNING,
                            rule_id=f"{self.RULE_PREFIX}_001",
                            message=f"Inconsistent capitalization for section '{section_name}'. Expected: '{canonical}'",
                            context=line.strip(),
                            suggestion=f"## {canonical}",
                        )
                    )
            else:
                # Check for typos using edit distance
                close_matches = self._find_close_matches(section_name)
                if close_matches:
                    issues.append(
                        Issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=IssueSeverity.INFO,
                            rule_id=f"{self.RULE_PREFIX}_002",
                            message=f"Unusual section name '{section_name}'. Did you mean: {', '.join(close_matches)}?",
                            context=line.strip(),
                            suggestion=f"## {close_matches[0]}",
                        )
                    )

        return issues

    def _find_close_matches(self, name: str, threshold: float = 0.7) -> list[str]:
        """Find section names within similarity threshold.

        Args:
            name: Section name to match
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of close matches from canonical sections
        """
        return difflib.get_close_matches(
            name.lower(), self.case_normalized.keys(), n=3, cutoff=threshold
        )
