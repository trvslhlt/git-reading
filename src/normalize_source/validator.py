"""Main validator orchestrating all validation rules."""

from pathlib import Path

from .models import Issue, ValidationResult
from .rules.citation_rules import CitationValidator
from .rules.header_rules import HeaderValidator
from .rules.list_rules import ListItemValidator
from .rules.section_rules import SectionNameValidator


class MarkdownValidator:
    """Main validator orchestrating all validation rules."""

    def __init__(
        self, use_patterns: bool = False, pattern_store_path: Path | None = None
    ):
        """Initialize the validator.

        Args:
            use_patterns: Whether to use pattern-based validation
            pattern_store_path: Path to learned patterns JSON file
        """
        # Rule-based validators
        self.validators = [
            HeaderValidator(),
            SectionNameValidator(),
            CitationValidator(),
            ListItemValidator(),
        ]

        # Pattern-based validator (optional)
        if use_patterns and pattern_store_path and pattern_store_path.exists():
            from .patterns.pattern_store import PatternStore
            from .patterns.pattern_validator import PatternValidator

            pattern_store = PatternStore.load(pattern_store_path)
            self.validators.append(PatternValidator(pattern_store))

    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate a single markdown file.

        Args:
            file_path: Path to the markdown file to validate

        Returns:
            ValidationResult containing all issues found
        """
        content = file_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        all_issues: list[Issue] = []
        for validator in self.validators:
            issues = validator.validate(lines, file_path)
            all_issues.extend(issues)

        # Sort issues by line number
        all_issues.sort(key=lambda i: i.line_number)

        return ValidationResult(file_path=file_path, issues=all_issues)

    def validate_directory(self, directory: Path) -> list[ValidationResult]:
        """Validate all markdown files in a directory.

        Args:
            directory: Directory containing markdown files

        Returns:
            List of ValidationResults, one per file
        """
        md_files = sorted(directory.glob("*.md"))
        return [self.validate_file(f) for f in md_files]
