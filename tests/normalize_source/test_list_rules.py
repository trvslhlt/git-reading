"""Tests for list item validation rules."""

import tempfile
from pathlib import Path

from normalize_source.rules.list_rules import ListItemValidator


def test_accepts_top_level_lists():
    """Test that top-level list items (0 spaces) are accepted."""
    content = """# Book Title

## notes
- Top level item
- Another top level item
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        validator = ListItemValidator()
        lines = content.splitlines()
        issues = validator.validate(lines, temp_path)

        assert len(issues) == 0
    finally:
        temp_path.unlink()


def test_accepts_single_level_nesting():
    """Test that 4-space nested items are accepted."""
    content = """# Book Title

## notes
- Top level item
    - Nested item (4 spaces)
    - Another nested item
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        validator = ListItemValidator()
        lines = content.splitlines()
        issues = validator.validate(lines, temp_path)

        assert len(issues) == 0
    finally:
        temp_path.unlink()


def test_accepts_multiple_level_nesting():
    """Test that multiple levels of nesting (8, 12 spaces) are accepted."""
    content = """# Book Title

## notes
- Top level item
    - First level nested (4 spaces)
        - Second level nested (8 spaces)
            - Third level nested (12 spaces)
    - Back to first level
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        validator = ListItemValidator()
        lines = content.splitlines()
        issues = validator.validate(lines, temp_path)

        assert len(issues) == 0
    finally:
        temp_path.unlink()


def test_flags_non_multiple_of_four_indentation():
    """Test that indentation not a multiple of 4 is flagged."""
    content = """# Book Title

## notes
- Top level
  - Two space indent (wrong)
   - Three space indent (wrong)
     - Five space indent (wrong)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        validator = ListItemValidator()
        lines = content.splitlines()
        issues = validator.validate(lines, temp_path)

        # Should flag the 2, 3, and 5 space indents
        assert len(issues) == 3

        # Check that all are LIST_002 issues
        for issue in issues:
            assert issue.rule_id == "LIST_002"
            assert "multiple of 4" in issue.message

        # Check that suggestions normalize to multiples of 4
        assert issues[0].suggestion == "- Two space indent (wrong)"  # 2 -> 0
        assert issues[1].suggestion == "- Three space indent (wrong)"  # 3 -> 0
        assert issues[2].suggestion == "    - Five space indent (wrong)"  # 5 -> 4
    finally:
        temp_path.unlink()


def test_flags_asterisk_and_plus():
    """Test that asterisk and plus bullets are flagged."""
    content = """# Book Title

## notes
* Using asterisk
+ Using plus
- Correct dash
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)

    try:
        validator = ListItemValidator()
        lines = content.splitlines()
        issues = validator.validate(lines, temp_path)

        # Should flag asterisk and plus
        assert len(issues) == 2
        assert all(i.rule_id == "LIST_001" for i in issues)
        assert "Using asterisk" in issues[0].context
        assert "Using plus" in issues[1].context
    finally:
        temp_path.unlink()
