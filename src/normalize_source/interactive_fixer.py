"""Interactive fix application."""

import json
from pathlib import Path

from .fixer import MarkdownFixer
from .models import Issue, IssueSeverity


class InteractiveFixer:
    """Interactively apply fixes from validation results."""

    def __init__(self, validation_json_path: Path, notes_dir: Path | None = None):
        """Initialize the interactive fixer.

        Args:
            validation_json_path: Path to validation JSON output
            notes_dir: Base directory for resolving relative file paths (default: current dir)
        """
        self.validation_json_path = validation_json_path
        self.notes_dir = notes_dir or Path(".")
        self.issues_with_suggestions = []
        self._load_issues()

    def _load_issues(self):
        """Load issues from validation JSON."""
        try:
            data = json.loads(self.validation_json_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to read validation JSON: {e}") from e

        # Extract issues with suggestions
        for file_data in data.get("files", []):
            # Resolve file path relative to notes_dir if it's not absolute
            file_path = Path(file_data["file"])
            if not file_path.is_absolute():
                file_path = self.notes_dir / file_path

            for issue_data in file_data.get("issues", []):
                if issue_data.get("suggestion"):
                    issue = Issue(
                        file_path=file_path,
                        line_number=issue_data["line"],
                        severity=IssueSeverity(issue_data["severity"]),
                        rule_id=issue_data["rule_id"],
                        message=issue_data["message"],
                        context=issue_data["context"],
                        suggestion=issue_data["suggestion"],
                    )
                    self.issues_with_suggestions.append(issue)

    def run(self, auto_yes: bool = False) -> dict:
        """Run the interactive fixer.

        Args:
            auto_yes: If True, automatically apply all fixes without prompting

        Returns:
            Dictionary with statistics about fixes applied
        """
        if not self.issues_with_suggestions:
            print("No issues with suggestions found.")
            return {"total": 0, "applied": 0, "skipped": 0, "failed": 0}

        print(f"\nFound {len(self.issues_with_suggestions)} fixable issues.\n")

        fixer = MarkdownFixer(dry_run=False)
        stats = {"total": len(self.issues_with_suggestions), "applied": 0, "skipped": 0, "failed": 0}

        for i, issue in enumerate(self.issues_with_suggestions, 1):
            print(f"[{i}/{stats['total']}] {issue.file_path}:{issue.line_number}")
            print(f"  Rule: {issue.rule_id}")
            print(f"  Message: {issue.message}")
            print(f"  Current: {issue.context}")
            print(f"  Suggestion: {issue.suggestion}")

            if auto_yes:
                choice = "y"
            else:
                choice = (
                    input("\nApply this fix? [y/n/q (quit)] ").strip().lower()
                )

            if choice == "q":
                print("\nQuitting...")
                break
            elif choice == "y":
                if fixer.apply_fix(issue):
                    print("✓ Applied")
                    stats["applied"] += 1
                else:
                    print("✗ Failed to apply")
                    stats["failed"] += 1
            else:
                print("Skipped")
                stats["skipped"] += 1

            print()  # Blank line between issues

        # Summary
        print("\n" + "=" * 60)
        print("Fix Summary:")
        print(f"  Total fixable issues: {stats['total']}")
        print(f"  Applied: {stats['applied']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")

        modified_files = fixer.get_modified_files()
        if modified_files:
            print(f"\nModified {len(modified_files)} file(s):")
            for file_path in sorted(modified_files):
                print(f"  - {file_path}")

        return stats
