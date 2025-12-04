"""Citation validation rules."""

import re
from pathlib import Path

from ..models import Issue, IssueSeverity


class CitationValidator:
    """Validates page number citations."""

    RULE_PREFIX = "CITATION"
    CITATION_PATTERN = re.compile(r"\(p\.\s+(\d+)\)")
    MALFORMED_PATTERNS = [
        (re.compile(r"\(p\.(\d+)\)"), "Missing space after 'p.'"),
        (re.compile(r"\(pg\.\s*\d+\)"), "Use 'p.' instead of 'pg.'"),
        (re.compile(r"\(page\s+\d+\)"), "Use 'p.' instead of 'page'"),
    ]

    def validate(self, lines: list[str], file_path: Path) -> list[Issue]:
        """Validate page number citations.

        Args:
            lines: List of lines from the markdown file
            file_path: Path to the file being validated

        Returns:
            List of validation issues found
        """
        issues = []
        current_section = None
        section_items: list[tuple[int, str]] = []

        for line_num, line in enumerate(lines, start=1):
            # Track current section
            if line.startswith("## "):
                # Analyze previous section
                if current_section:
                    issues.extend(
                        self._check_section_consistency(section_items, file_path, current_section)
                    )
                current_section = line.strip()
                section_items = []
                continue

            # Check list items (only top-level items, not nested)
            stripped = line.strip()
            if stripped.startswith("- ") and not line.startswith("    "):
                section_items.append((line_num, line))

                # Check for malformed citations
                for pattern, error_msg in self.MALFORMED_PATTERNS:
                    if pattern.search(line):
                        # Suggest correct format
                        suggestion = self._suggest_citation_fix(line, pattern)
                        issues.append(
                            Issue(
                                file_path=file_path,
                                line_number=line_num,
                                severity=IssueSeverity.ERROR,
                                rule_id=f"{self.RULE_PREFIX}_001",
                                message=f"Malformed page citation: {error_msg}",
                                context=line.strip(),
                                suggestion=suggestion,
                            )
                        )

        # Check last section
        if current_section and section_items:
            issues.extend(
                self._check_section_consistency(section_items, file_path, current_section)
            )

        return issues

    def _check_section_consistency(
        self, items: list[tuple[int, str]], file_path: Path, section_name: str
    ) -> list[Issue]:
        """Check if citations are consistent within a section.

        Args:
            items: List of (line_number, line_text) tuples
            file_path: Path to the file being validated
            section_name: Name of the section being checked

        Returns:
            List of validation issues found
        """
        issues = []

        # Flag missing citations when the previous line had a citation
        # but allow if no subsequent notes have citations
        for i, (line_num, line) in enumerate(items):
            has_citation = bool(self.CITATION_PATTERN.search(line))

            if not has_citation and i > 0:
                # Check if previous line had a citation
                _, prev_line = items[i - 1]
                prev_has_citation = bool(self.CITATION_PATTERN.search(prev_line))

                if prev_has_citation:
                    # Check if any subsequent items have citations
                    subsequent_items = items[i:]
                    any_subsequent_citations = any(
                        bool(self.CITATION_PATTERN.search(item_line))
                        for _, item_line in subsequent_items
                    )

                    # Only flag if there are more citations later
                    # (indicates we're in the middle of cited content)
                    if any_subsequent_citations:
                        issues.append(
                            Issue(
                                file_path=file_path,
                                line_number=line_num,
                                severity=IssueSeverity.WARNING,
                                rule_id=f"{self.RULE_PREFIX}_002",
                                message=f"Missing page citation after item with citation in section '{section_name}'",
                                context=line.strip(),
                                suggestion=None,
                            )
                        )

        return issues

    def _suggest_citation_fix(self, line: str, pattern: re.Pattern) -> str:
        """Suggest a corrected citation format.

        Args:
            line: Line with malformed citation
            pattern: Pattern that matched the malformed citation

        Returns:
            Suggested corrected line
        """
        # Extract the page number
        match = pattern.search(line)
        if not match:
            return line

        # Find the page number in the match
        page_num_match = re.search(r"\d+", match.group(0))
        if page_num_match:
            page_num = page_num_match.group(0)
            # Replace the malformed citation with correct format
            corrected = pattern.sub(f"(p. {page_num})", line)
            return corrected.strip()

        return line.strip()
