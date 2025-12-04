"""Tests for the fixer module."""

import tempfile
from pathlib import Path

from normalize_source.fixer import MarkdownFixer
from normalize_source.models import Issue, IssueSeverity


def test_apply_fix_success():
    """Test successfully applying a fix."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Test Book\n")
        f.write("## Notes\n")
        f.write("- Item one\n")
        temp_path = Path(f.name)

    try:
        # Create an issue with a suggestion
        issue = Issue(
            file_path=temp_path,
            line_number=2,
            severity=IssueSeverity.WARNING,
            rule_id="SECTION_001",
            message="Inconsistent capitalization",
            context="## Notes",
            suggestion="## notes",
        )

        # Apply the fix
        fixer = MarkdownFixer(dry_run=False)
        result = fixer.apply_fix(issue)

        assert result is True
        assert temp_path in fixer.get_modified_files()

        # Verify the file was modified
        content = temp_path.read_text()
        assert "## notes" in content
        assert "## Notes" not in content

    finally:
        # Cleanup
        temp_path.unlink()


def test_apply_fix_dry_run():
    """Test dry run mode doesn't modify files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("## Notes\n")
        temp_path = Path(f.name)

    try:
        issue = Issue(
            file_path=temp_path,
            line_number=1,
            severity=IssueSeverity.WARNING,
            rule_id="SECTION_001",
            message="Test",
            context="## Notes",
            suggestion="## notes",
        )

        fixer = MarkdownFixer(dry_run=True)
        result = fixer.apply_fix(issue)

        assert result is True
        assert temp_path in fixer.get_modified_files()

        # Verify the file was NOT modified
        content = temp_path.read_text()
        assert "## Notes" in content
        assert "## notes" not in content

    finally:
        temp_path.unlink()


def test_apply_fix_context_mismatch():
    """Test that fix fails if context doesn't match."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("## Different Content\n")
        temp_path = Path(f.name)

    try:
        issue = Issue(
            file_path=temp_path,
            line_number=1,
            severity=IssueSeverity.WARNING,
            rule_id="SECTION_001",
            message="Test",
            context="## Notes",  # This doesn't match actual content
            suggestion="## notes",
        )

        fixer = MarkdownFixer(dry_run=False)
        result = fixer.apply_fix(issue)

        assert result is False
        assert temp_path not in fixer.get_modified_files()

    finally:
        temp_path.unlink()


def test_apply_fix_no_suggestion():
    """Test that fix returns False when there's no suggestion."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("## Notes\n")
        temp_path = Path(f.name)

    try:
        issue = Issue(
            file_path=temp_path,
            line_number=1,
            severity=IssueSeverity.WARNING,
            rule_id="CITATION_002",
            message="Missing citation",
            context="- Note without citation",
            suggestion=None,  # No suggestion
        )

        fixer = MarkdownFixer(dry_run=False)
        result = fixer.apply_fix(issue)

        assert result is False
        assert temp_path not in fixer.get_modified_files()

    finally:
        temp_path.unlink()


def test_apply_multiple_fixes():
    """Test applying multiple fixes to the same file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("## Notes\n")
        f.write("## Threads\n")
        f.write("## Excerpts\n")
        temp_path = Path(f.name)

    try:
        issues = [
            Issue(
                file_path=temp_path,
                line_number=1,
                severity=IssueSeverity.WARNING,
                rule_id="SECTION_001",
                message="Test",
                context="## Notes",
                suggestion="## notes",
            ),
            Issue(
                file_path=temp_path,
                line_number=2,
                severity=IssueSeverity.WARNING,
                rule_id="SECTION_001",
                message="Test",
                context="## Threads",
                suggestion="## threads",
            ),
        ]

        fixer = MarkdownFixer(dry_run=False)

        for issue in issues:
            result = fixer.apply_fix(issue)
            assert result is True

        # Should only count as one modified file
        assert len(fixer.get_modified_files()) == 1

        # Verify both fixes were applied
        content = temp_path.read_text()
        assert "## notes" in content
        assert "## threads" in content
        assert "## Notes" not in content
        assert "## Threads" not in content

    finally:
        temp_path.unlink()
