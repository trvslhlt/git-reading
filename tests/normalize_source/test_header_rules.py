"""Tests for header validation rules."""

from pathlib import Path

import pytest

from normalize_source.models import IssueSeverity
from normalize_source.rules.header_rules import HeaderValidator


def test_detects_triple_hash_headers():
    """Test that triple ### headers are flagged as errors."""
    validator = HeaderValidator()
    lines = ["# Book Title", "### Invalid Section"]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 1
    assert issues[0].severity == IssueSeverity.ERROR
    assert issues[0].line_number == 2
    assert "level 2" in issues[0].message.lower()


def test_detects_missing_space_after_hash():
    """Test that headers without space after # are flagged."""
    validator = HeaderValidator()
    lines = ["#Book Title", "##Section"]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 2
    assert all(i.severity == IssueSeverity.ERROR for i in issues)
    assert all("space" in i.message.lower() for i in issues)


def test_accepts_valid_headers():
    """Test that valid headers pass validation."""
    validator = HeaderValidator()
    lines = ["# Book Title", "## Section Name", "Some content"]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 0


def test_provides_suggestions():
    """Test that suggestions are provided for fixable issues."""
    validator = HeaderValidator()
    lines = ["#Book Title"]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 1
    assert issues[0].suggestion is not None
    assert issues[0].suggestion == "# Book Title"


def test_detects_canonical_section_name_as_book_title():
    """Test that canonical section names used as book titles are flagged."""
    validator = HeaderValidator()
    lines = ["# terms", "", "## notes", "- Some note"]

    issues = validator.validate(lines, Path("test.md"))

    # Should flag "terms" as a book title
    assert len(issues) == 1
    assert issues[0].rule_id == "HEADER_003"
    assert issues[0].severity == IssueSeverity.ERROR
    assert "canonical section name" in issues[0].message
    assert "terms" in issues[0].message


def test_detects_multiple_canonical_section_names_as_titles():
    """Test that multiple canonical section names as book titles are all flagged."""
    validator = HeaderValidator()
    lines = [
        "# notes",
        "",
        "## terms",
        "- Term one",
        "",
        "# excerpts",
        "",
        "## threads",
        "- Thread one",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should flag both "notes" and "excerpts" as book titles
    header_003_issues = [i for i in issues if i.rule_id == "HEADER_003"]
    assert len(header_003_issues) == 2
    assert any("notes" in i.message for i in header_003_issues)
    assert any("excerpts" in i.message for i in header_003_issues)


def test_accepts_canonical_section_names_at_level_2():
    """Test that canonical section names at level 2 (##) are accepted."""
    validator = HeaderValidator()
    lines = [
        "# Valid Book Title",
        "",
        "## terms",
        "- Term one",
        "",
        "## notes",
        "- Note one",
        "",
        "## excerpts",
        "- Excerpt one",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag section names at level 2
    header_003_issues = [i for i in issues if i.rule_id == "HEADER_003"]
    assert len(header_003_issues) == 0


def test_case_insensitive_canonical_section_detection():
    """Test that canonical section name detection is case-insensitive."""
    validator = HeaderValidator()
    lines = [
        "# Terms",
        "",
        "## notes",
        "- Some note",
        "",
        "# NOTES",
        "",
        "## terms",
        "- Some term",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should flag both "Terms" and "NOTES" as book titles
    header_003_issues = [i for i in issues if i.rule_id == "HEADER_003"]
    assert len(header_003_issues) == 2


def test_accepts_non_canonical_book_titles():
    """Test that non-canonical book titles are accepted."""
    validator = HeaderValidator()
    lines = [
        "# The Great Gatsby",
        "",
        "## notes",
        "- Note about the book",
        "",
        "# 1984",
        "",
        "## excerpts",
        "- Famous quote",
    ]

    issues = validator.validate(lines, Path("test.md"))

    # Should not flag non-canonical book titles
    header_003_issues = [i for i in issues if i.rule_id == "HEADER_003"]
    assert len(header_003_issues) == 0


def test_detects_all_canonical_section_names():
    """Test that all canonical section names are detected when used as book titles."""
    validator = HeaderValidator()
    # Test a sampling of canonical section names
    canonical_names = ["terms", "notes", "excerpts", "threads", "ideas", "same time"]
    lines = []
    for name in canonical_names:
        lines.extend([f"# {name}", "", "## some section", "- content", ""])

    issues = validator.validate(lines, Path("test.md"))

    header_003_issues = [i for i in issues if i.rule_id == "HEADER_003"]
    assert len(header_003_issues) == len(canonical_names)
