"""Tests for citation validation rules."""

from pathlib import Path

from normalize_source.models import IssueSeverity
from normalize_source.rules.citation_rules import CitationValidator


def test_missing_citation_allowed_at_end():
    """Test that missing citation is allowed if no subsequent citations."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) Note with citation",
        "- Note without citation",
        "- Another note without citation",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag missing citations at the end
    assert len(issues) == 0


def test_missing_citation_flagged_in_middle():
    """Test that missing citation is flagged if there are subsequent citations."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) First note with citation",
        "- Note without citation",  # Should be flagged
        "- (p. 20) Another note with citation",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should flag the middle note without citation
    assert len(issues) == 1
    assert issues[0].line_number == 3
    assert issues[0].severity == IssueSeverity.WARNING


def test_multiple_missing_citations_at_end():
    """Test that multiple missing citations at end are all allowed."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) Note with citation",
        "- Note without citation",
        "- Another note without citation",
        "- Yet another note without citation",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag any missing citations at the end
    assert len(issues) == 0


def test_alternating_citations():
    """Test alternating pattern of citations."""
    validator = CitationValidator()
    lines = [
        "## notes",
        "- (p. 10) First",
        "- No citation",  # Flagged (has subsequent citation)
        "- (p. 20) Second",
        "- No citation",  # Flagged (has subsequent citation)
        "- (p. 30) Third",
        "- No citation",  # Not flagged (no subsequent citations)
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should flag lines 3 and 5 only
    assert len(issues) == 2
    assert issues[0].line_number == 3
    assert issues[1].line_number == 5
