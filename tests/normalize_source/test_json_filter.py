"""Test JSON output filtering."""

import json
from pathlib import Path

from normalize_source.models import Issue, IssueSeverity, ValidationResult
from normalize_source.reporters import ValidationReporter


def test_json_filters_clean_files():
    """Test that JSON output excludes files with no issues."""
    # Create mock results with one clean and one with issues
    clean_result = ValidationResult(file_path=Path("clean.md"), issues=[])

    issue = Issue(
        file_path=Path("dirty.md"),
        line_number=1,
        severity=IssueSeverity.WARNING,
        rule_id="TEST_001",
        message="Test issue",
        context="test context",
        suggestion=None,
    )

    dirty_result = ValidationResult(file_path=Path("dirty.md"), issues=[issue])

    results = [clean_result, dirty_result]

    reporter = ValidationReporter()
    json_output = reporter.report_json(results)

    # Check that only dirty.md appears in JSON
    assert "dirty.md" in json_output
    assert "clean.md" not in json_output

    # Parse JSON and verify structure
    data = json.loads(json_output)

    assert len(data["files"]) == 1
    assert data["files"][0]["file"] == "dirty.md"
    assert len(data["files"][0]["issues"]) == 1


def test_json_empty_when_all_clean():
    """Test that JSON output has empty files array when all files are clean."""
    clean_result1 = ValidationResult(file_path=Path("file1.md"), issues=[])
    clean_result2 = ValidationResult(file_path=Path("file2.md"), issues=[])

    results = [clean_result1, clean_result2]

    reporter = ValidationReporter()
    json_output = reporter.report_json(results)

    data = json.loads(json_output)

    assert len(data["files"]) == 0
