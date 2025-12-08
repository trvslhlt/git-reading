"""Header validation rules."""

import re
from pathlib import Path

from common.constants import CANONICAL_SECTIONS

from ..models import Issue, IssueSeverity


class HeaderValidator:
    """Validates markdown header structure."""

    RULE_PREFIX = "HEADER"

    def validate(self, lines: list[str], file_path: Path) -> list[Issue]:
        """Validate header structure in markdown content.

        Args:
            lines: List of lines from the markdown file
            file_path: Path to the file being validated

        Returns:
            List of validation issues found
        """
        issues = []

        for line_num, line in enumerate(lines, start=1):
            # Check for level 1 headers (book titles) that are canonical section names
            if line.startswith("# ") and not line.startswith("## "):
                title = line[2:].strip().lower()
                if title in CANONICAL_SECTIONS:
                    issues.append(
                        Issue(
                            file_path=file_path,
                            line_number=line_num,
                            severity=IssueSeverity.ERROR,
                            rule_id=f"{self.RULE_PREFIX}_003",
                            message=f"Book title '{line[2:].strip()}' is a canonical section name and should not be used as a book title",
                            context=line.strip(),
                            suggestion=None,
                        )
                    )

            # Check for headers deeper than level 2
            if line.startswith("###"):
                issues.append(
                    Issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=IssueSeverity.ERROR,
                        rule_id=f"{self.RULE_PREFIX}_001",
                        message="Headers deeper than level 2 are not supported",
                        context=line.strip(),
                        suggestion="Use ## for sections within books",
                    )
                )

            # Check for missing space after # (but not for multiple consecutive #)
            if re.match(r"^#{1,2}[^\s#]", line):
                suggested_line = re.sub(r"^(#{1,2})(\S)", r"\1 \2", line)
                issues.append(
                    Issue(
                        file_path=file_path,
                        line_number=line_num,
                        severity=IssueSeverity.ERROR,
                        rule_id=f"{self.RULE_PREFIX}_002",
                        message="Missing space after # in header",
                        context=line.strip(),
                        suggestion=suggested_line.strip(),
                    )
                )

        return issues
