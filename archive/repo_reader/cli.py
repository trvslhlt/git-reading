"""Command line entry point for repository Q&A."""
from __future__ import annotations

import argparse
import sys

from .app import RepositoryQAApp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Ask a one-off question about the repo")
    parser.add_argument("--repo", default=".", help="Path to the git repository root")
    parser.add_argument("--limit", type=int, default=5, help="Number of answer snippets to show")
    parser.add_argument("--max-commits", type=int, default=50, help="How many recent commits to load")
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=200_000,
        help="Maximum bytes to read per file",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start an interactive prompt after building the index",
    )
    args = parser.parse_args(argv)

    app = RepositoryQAApp(
        args.repo,
        max_commits=args.max_commits,
        max_file_bytes=args.max_file_bytes,
    )
    app.build()
    print(app.summarize())

    if args.interactive:
        return _interactive_loop(app, limit=args.limit)

    if not args.question:
        parser.error("Provide a question or use --interactive")
    _print_answers(app, args.question, limit=args.limit)
    return 0


def _interactive_loop(app: RepositoryQAApp, *, limit: int) -> int:
    print("Enter a question (empty line to exit).")
    try:
        while True:
            try:
                question = input("? ")
            except EOFError:
                print()
                break
            if not question.strip():
                break
            _print_answers(app, question, limit=limit)
    except KeyboardInterrupt:
        print()
        return 130
    return 0


def _print_answers(app: RepositoryQAApp, question: str, *, limit: int) -> None:
    answers = app.ask(question, limit=limit)
    if not answers:
        print("No relevant snippets found.")
        return
    print(f"Top {len(answers)} results for: {question}")
    for idx, candidate in enumerate(answers, start=1):
        print(f"[{idx}] {candidate.source} :: {candidate.location} :: score={candidate.score:.3f}")
        print(candidate.excerpt)
        print("-" * 60)


if __name__ == "__main__":
    sys.exit(main())
