"""List item validation rules."""

import re
from pathlib import Path

from ..models import Issue, IssueSeverity


class ListItemValidator:
    """Validates list item formatting."""

    RULE_PREFIX = "LIST"

    def validate(self, lines: list[str], file_path: Path) -> list[Issue]:
        """Validate list item formatting.

        Args:
            lines: List of lines from the markdown file
            file_path: Path to the file being validated

        Returns:
            List of validation issues found
        """
        issues = []

        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines and headers
            if not line.strip() or line.startswith("#"):
                continue

            # Check for lines that look like list items but don't use proper syntax
            # (Lines starting with asterisk or plus instead of dash)
            if re.match(r"^\s*[\*\+]\s", line):
                issues.append(
                    Issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=IssueSeverity.WARNING,
                        rule_id=f"{self.RULE_PREFIX}_001",
                        message="Use '-' for list items instead of '*' or '+'",
                        context=line.strip(),
                        suggestion=re.sub(r"^(\s*)[\*\+]", r"\1-", line).strip(),
                    )
                )

            # Check for improper indentation of list items
            # Allow 4-space indentation for nested content, but flag other amounts
            if re.match(r"^( {1,3}| {5,})-\s", line):
                issues.append(
                    Issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=IssueSeverity.WARNING,
                        rule_id=f"{self.RULE_PREFIX}_002",
                        message="Unexpected indentation for list item (use 0 spaces for top-level, 4 spaces for nested)",
                        context=line.strip(),
                        suggestion=line.lstrip().strip(),
                    )
                )

        return issues
