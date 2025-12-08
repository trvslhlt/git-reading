"""Apply fixes to markdown files based on validation results."""

from pathlib import Path

from common.logger import get_logger

from .models import Issue

logger = get_logger(__name__)


class MarkdownFixer:
    """Applies fixes to markdown files."""

    def __init__(self, dry_run: bool = False):
        """Initialize the fixer.

        Args:
            dry_run: If True, don't actually write changes to files
        """
        self.dry_run = dry_run
        self.files_modified = set()

    def apply_fix(self, issue: Issue) -> bool:
        """Apply a single fix to a file.

        Args:
            issue: The issue with a suggestion to apply

        Returns:
            True if fix was applied successfully, False otherwise
        """
        if not issue.suggestion:
            return False

        file_path = issue.file_path
        line_number = issue.line_number

        # Read the file
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return False

        # Check if line number is valid
        if line_number < 1 or line_number > len(lines):
            logger.error(f"Invalid line number {line_number} in {file_path}")
            return False

        # Get the line (convert to 0-indexed)
        line_idx = line_number - 1
        original_line = lines[line_idx].rstrip("\n\r")

        # Verify the line matches the context (safety check)
        if original_line.strip() != issue.context.strip():
            logger.warning(f"Line {line_number} in {file_path} doesn't match expected context")
            logger.warning(f"  Expected: {issue.context}")
            logger.warning(f"  Found: {original_line}")
            return False

        # Apply the fix (preserve original line ending)
        line_ending = lines[line_idx][len(original_line) :]
        lines[line_idx] = issue.suggestion + line_ending

        # Write back to file (unless dry run)
        if not self.dry_run:
            try:
                file_path.write_text("".join(lines), encoding="utf-8")
                self.files_modified.add(file_path)
                return True
            except Exception as e:
                logger.error(f"Error writing {file_path}: {e}")
                return False
        else:
            # In dry run, just mark as modified
            self.files_modified.add(file_path)
            return True

    def get_modified_files(self) -> set[Path]:
        """Get the set of files that were modified.

        Returns:
            Set of file paths that were modified
        """
        return self.files_modified
