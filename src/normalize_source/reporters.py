"""Validation result reporters."""

import json

from .models import IssueSeverity, ValidationResult


class ValidationReporter:
    """Format and display validation results."""

    def __init__(self, show_info: bool = True):
        """Initialize the reporter.

        Args:
            show_info: Whether to show info-level messages
        """
        self.show_info = show_info

    def report_console(self, results: list[ValidationResult]) -> int:
        """Print validation results to console.

        Args:
            results: List of validation results to report

        Returns:
            Exit code (0 for success, 1 if errors found)
        """
        total_errors = 0
        total_warnings = 0
        total_info = 0

        for result in results:
            if result.is_clean:
                continue

            print(f"\n{result.file_path.name}:")

            for issue in result.issues:
                if issue.severity == IssueSeverity.ERROR:
                    total_errors += 1
                    icon = "✗"
                elif issue.severity == IssueSeverity.WARNING:
                    total_warnings += 1
                    icon = "⚠"
                else:
                    total_info += 1
                    icon = "ℹ"

                if not self.show_info and issue.severity == IssueSeverity.INFO:
                    continue

                print(f"  {icon} Line {issue.line_number}: {issue.message}")
                print(f"      {issue.context}")
                if issue.suggestion:
                    print(f"      Suggestion: {issue.suggestion}")

        # Summary
        print("\n" + "=" * 60)
        print(f"Total: {total_errors} errors, {total_warnings} warnings, {total_info} info")

        if total_errors > 0:
            return 1  # Exit code for errors
        return 0

    def report_json(self, results: list[ValidationResult]) -> str:
        """Format results as JSON.

        Args:
            results: List of validation results to report

        Returns:
            JSON string representation of results
        """
        # Filter out files with no issues
        results_with_issues = [r for r in results if not r.is_clean]

        data = {
            "files": [
                {
                    "file": str(r.file_path),
                    "issues": [
                        {
                            "line": i.line_number,
                            "severity": i.severity.value,
                            "rule_id": i.rule_id,
                            "message": i.message,
                            "context": i.context,
                            "suggestion": i.suggestion,
                        }
                        for i in r.issues
                    ],
                }
                for r in results_with_issues
            ]
        }

        return json.dumps(data, indent=2)
