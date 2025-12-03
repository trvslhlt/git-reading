#!/usr/bin/env python3
"""Validate markdown reading notes for structural and formatting issues.

Usage:
    python -m normalize_source.main validate [--notes-dir PATH] [--patterns PATH]
    python -m normalize_source.main learn [--notes-dir PATH] [--output PATH]
"""

import argparse
from pathlib import Path

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
        print(reporter.report_json(results))
        return 0
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
    validate_parser.add_argument(
        "--patterns", type=str, help="Path to learned patterns JSON file"
    )
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
        "--show-info",
        action="store_true",
        default=True,
        help="Show info-level messages",
    )
    validate_parser.set_defaults(func=cmd_validate)

    # Learn command
    learn_parser = subparsers.add_parser(
        "learn", help="Learn patterns from markdown files"
    )
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

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    exit(main())
