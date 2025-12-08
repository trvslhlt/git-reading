"""Content validation rules for checking empty books and sections."""

from pathlib import Path

from common.constants import CANONICAL_SECTIONS

from ..models import Issue, IssueSeverity


class ContentValidator:
    """Validates that books and sections have content."""

    RULE_PREFIX = "CONTENT"

    def validate(self, lines: list[str], file_path: Path) -> list[Issue]:
        """Validate that books and sections have content.

        Args:
            lines: List of lines from the markdown file
            file_path: Path to the file being validated

        Returns:
            List of validation issues found
        """
        issues = []

        # Track current book and section
        current_book = None
        current_book_line = None
        current_section = None
        current_section_line = None
        current_section_has_content = False
        current_book_has_content = False

        # Section names that shouldn't be treated as book titles
        section_names = CANONICAL_SECTIONS

        def check_empty_section():
            """Check if the current section is empty and add issue if so."""
            nonlocal current_section, current_section_line, current_section_has_content
            if current_section and not current_section_has_content:
                issues.append(
                    Issue(
                        file_path=file_path,
                        line_number=current_section_line,
                        severity=IssueSeverity.ERROR,
                        rule_id=f"{self.RULE_PREFIX}_001",
                        message=f'Section "{current_section}" has no content',
                        context=f"## {current_section}",
                        suggestion="Add content to the section or remove it",
                    )
                )

        def check_empty_book():
            """Check if the current book is empty and add issue if so."""
            nonlocal current_book, current_book_line, current_book_has_content
            if current_book and not current_book_has_content:
                issues.append(
                    Issue(
                        file_path=file_path,
                        line_number=current_book_line,
                        severity=IssueSeverity.ERROR,
                        rule_id=f"{self.RULE_PREFIX}_002",
                        message=f'Book "{current_book}" has no sections with content',
                        context=f"# {current_book}",
                        suggestion="Add sections with content to the book",
                    )
                )

        for line_num, line in enumerate(lines, start=1):
            # Check for book title (# Title)
            if line.startswith("# ") and not line.startswith("## "):
                potential_title = line[2:].strip()

                # Skip if this looks like a section name, not a book title
                if potential_title.lower() in section_names:
                    # This is a section, not a book - handle it as a section
                    check_empty_section()
                    current_section = potential_title
                    current_section_line = line_num
                    current_section_has_content = False
                    continue

                # This is a new book - check previous section and book
                check_empty_section()
                check_empty_book()

                # Start tracking new book
                current_book = potential_title
                current_book_line = line_num
                current_book_has_content = False
                current_section = None
                current_section_line = None
                current_section_has_content = False

            # Check for section header (## Section)
            elif line.startswith("## "):
                # Check previous section
                check_empty_section()

                # Start tracking new section
                current_section = line[3:].strip()
                current_section_line = line_num
                current_section_has_content = False

            # Content line (could be a list item or paragraph)
            elif current_book and current_section:
                stripped = line.strip()
                if stripped:
                    # Check if this is content (not just whitespace or metadata)
                    if stripped.startswith("- ") or (stripped and not stripped.startswith("#")):
                        # This section has content
                        current_section_has_content = True
                        current_book_has_content = True

        # Don't forget to check the last section and book
        check_empty_section()
        check_empty_book()

        return issues
