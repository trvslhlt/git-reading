#!/usr/bin/env python3
"""CLI interface for normalize_source module."""

import argparse
import io
import sys
from pathlib import Path

from .interactive_fixer import InteractiveFixer
from .patterns.learner import PatternLearner
from .reporters import ValidationReporter
from .validator import MarkdownValidator


def cmd_validate(args):
    """Run validation on markdown files.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    notes_dir = Path(args.notes_dir)

    if not notes_dir.exists():
        print(f"Error: Directory '{notes_dir}' does not exist")
        return 1

    validator = MarkdownValidator(
        use_patterns=args.use_patterns,
        pattern_store_path=Path(args.patterns) if args.patterns else None,
    )

    results = validator.validate_directory(notes_dir)

    reporter = ValidationReporter(show_info=args.show_info)

    if args.format == "json":
        output = reporter.report_json(results)
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(output, encoding="utf-8")
            print(f"Validation results written to {output_path}")
            return 0
        else:
            print(output)
            return 0
    else:
        # For console format, we can also optionally save to file
        if args.output:
            # Capture console output to file
            output_path = Path(args.output)
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            try:
                exit_code = reporter.report_console(results)
                output = buffer.getvalue()
                output_path.write_text(output, encoding="utf-8")

                # Also print to console
                sys.stdout = old_stdout
                print(output, end="")
                print(f"\nValidation results also written to {output_path}")
                return exit_code
            finally:
                sys.stdout = old_stdout
        else:
            return reporter.report_console(results)


def cmd_learn(args):
    """Learn patterns from markdown files.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    notes_dir = Path(args.notes_dir)
    output_path = Path(args.output)

    if not notes_dir.exists():
        print(f"Error: Directory '{notes_dir}' does not exist")
        return 1

    print(f"Learning patterns from {notes_dir}...")
    learner = PatternLearner()
    pattern_store = learner.learn_from_directory(notes_dir)

    pattern_store.save(output_path)
    print(f"Patterns saved to {output_path}")

    # Print summary
    for pattern_type, patterns in pattern_store.patterns.items():
        print(f"\n{pattern_type.upper()}:")
        for p in patterns[:5]:  # Top 5
            print(f"  - {p.value} (freq={p.frequency}, conf={p.confidence:.2f})")

    return 0


def cmd_fix(args):
    """Interactively apply fixes from validation results.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    validation_json = Path(args.validation)
    notes_dir = Path(args.notes_dir)

    if not validation_json.exists():
        print(f"Error: Validation JSON file '{validation_json}' does not exist")
        return 1

    if not notes_dir.exists():
        print(f"Error: Notes directory '{notes_dir}' does not exist")
        return 1

    try:
        fixer = InteractiveFixer(validation_json, notes_dir=notes_dir)
        stats = fixer.run(auto_yes=args.yes)

        # Return non-zero if any fixes failed
        if stats["failed"] > 0:
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Validate markdown reading notes")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate markdown files")
    validate_parser.add_argument(
        "--notes-dir",
        type=str,
        default=".",
        help="Directory containing markdown notes",
    )
    validate_parser.add_argument("--patterns", type=str, help="Path to learned patterns JSON file")
    validate_parser.add_argument(
        "--use-patterns",
        action="store_true",
        help="Use learned patterns for validation",
    )
    validate_parser.add_argument(
        "--format",
        choices=["console", "json"],
        default="console",
        help="Output format",
    )
    validate_parser.add_argument(
        "--output",
        type=str,
        help="Write validation results to file (in addition to console for console format)",
    )
    validate_parser.add_argument(
        "--show-info",
        action="store_true",
        default=True,
        help="Show info-level messages",
    )
    validate_parser.set_defaults(func=cmd_validate)

    # Learn command
    learn_parser = subparsers.add_parser("learn", help="Learn patterns from markdown files")
    learn_parser.add_argument(
        "--notes-dir", type=str, default=".", help="Directory containing markdown notes"
    )
    learn_parser.add_argument(
        "--output",
        type=str,
        default="patterns.json",
        help="Output path for learned patterns",
    )
    learn_parser.set_defaults(func=cmd_learn)

    # Fix command
    fix_parser = subparsers.add_parser(
        "fix", help="Interactively apply fixes from validation results"
    )
    fix_parser.add_argument(
        "--validation",
        type=str,
        required=True,
        help="Path to validation JSON file",
    )
    fix_parser.add_argument(
        "--notes-dir",
        type=str,
        default=".",
        help="Directory containing markdown notes (default: current directory)",
    )
    fix_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Automatically apply all fixes without prompting",
    )
    fix_parser.set_defaults(func=cmd_fix)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    exit(main())
