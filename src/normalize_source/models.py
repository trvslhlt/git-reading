"""Data models for validation results and patterns."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class IssueSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"  # Definite problems (e.g., wrong header level)
    WARNING = "warning"  # Likely problems (e.g., inconsistent capitalization)
    INFO = "info"  # Potential issues (e.g., unusual section name)


@dataclass
class Issue:
    """A single validation issue."""

    file_path: Path
    line_number: int
    severity: IssueSeverity
    rule_id: str  # e.g., "HEADER_001"
    message: str
    context: str  # The actual line content
    suggestion: str | None = None  # Suggested fix


@dataclass
class ValidationResult:
    """Result of validating a file or set of files."""

    file_path: Path
    issues: list[Issue]

    @property
    def has_errors(self) -> bool:
        """Check if result contains any errors."""
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        """Check if result contains any warnings."""
        return any(i.severity == IssueSeverity.WARNING for i in self.issues)

    @property
    def is_clean(self) -> bool:
        """Check if result has no issues."""
        return len(self.issues) == 0


@dataclass
class Pattern:
    """A learned pattern from corpus analysis."""

    pattern_type: str  # e.g., "section_name", "citation_format"
    value: str
    frequency: int
    confidence: float  # 0.0 to 1.0
    examples: list[str]  # Example occurrences
