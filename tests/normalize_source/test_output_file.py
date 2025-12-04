"""Test validation output to file functionality."""

import tempfile
from pathlib import Path

from normalize_source.cli import cmd_validate


class Args:
    """Mock arguments for testing."""

    def __init__(self, **kwargs):
        self.notes_dir = kwargs.get("notes_dir", ".")
        self.patterns = kwargs.get("patterns", None)
        self.use_patterns = kwargs.get("use_patterns", False)
        self.format = kwargs.get("format", "console")
        self.output = kwargs.get("output", None)
        self.show_info = kwargs.get("show_info", True)


def test_json_output_to_file(tmp_path):
    """Test that JSON output can be written to a file."""
    # Create a test markdown file with an issue
    test_file = tmp_path / "test.md"
    test_file.write_text("###Invalid Header\n")

    # Create output file path
    output_file = tmp_path / "output.json"

    # Run validation
    args = Args(notes_dir=str(tmp_path), format="json", output=str(output_file))
    cmd_validate(args)

    # Verify output file was created
    assert output_file.exists()

    # Verify it contains valid JSON
    import json

    data = json.loads(output_file.read_text())
    assert "files" in data
    assert len(data["files"]) > 0


def test_console_output_to_file(tmp_path):
    """Test that console output can be written to a file."""
    # Create a test markdown file
    test_file = tmp_path / "test.md"
    test_file.write_text("# Valid Book\n## notes\n- Item\n")

    # Create output file path
    output_file = tmp_path / "output.txt"

    # Run validation
    args = Args(notes_dir=str(tmp_path), format="console", output=str(output_file))
    cmd_validate(args)

    # Verify output file was created
    assert output_file.exists()

    # Verify it contains expected content
    content = output_file.read_text()
    assert "test.md" in content or "No issues" in content
