"""Tests for section name validation rules."""

import pytest
from pathlib import Path

from normalize_source.models import IssueSeverity
from normalize_source.rules.section_rules import SectionNameValidator


def test_detects_capitalization_inconsistency():
    """Test that inconsistent capitalization is flagged."""
    validator = SectionNameValidator()
    lines = ["## Threads"]  # Should be lowercase

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 1
    assert issues[0].severity == IssueSeverity.WARNING
    assert "threads" in issues[0].suggestion


def test_accepts_canonical_section_names():
    """Test that canonical section names pass validation."""
    validator = SectionNameValidator()
    lines = ["## threads", "## notes", "## excerpts", "## terms"]

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 0


def test_suggests_close_matches_for_typos():
    """Test that typos suggest close matches."""
    validator = SectionNameValidator()
    lines = ["## threeds"]  # Typo

    issues = validator.validate(lines, Path("test.md"))

    assert len(issues) == 1
    assert issues[0].severity == IssueSeverity.INFO
    assert "unusual" in issues[0].message.lower()


def test_case_insensitive_matching():
    """Test that section names are matched case-insensitively."""
    validator = SectionNameValidator()
    lines = ["## NOTES", "## Notes", "## NoTeS"]

    issues = validator.validate(lines, Path("test.md"))

    # All should be flagged for inconsistent capitalization
    assert len(issues) == 3
    assert all(i.severity == IssueSeverity.WARNING for i in issues)
