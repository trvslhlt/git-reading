"""Tests for header validation rules."""

import pytest
from pathlib import Path

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
