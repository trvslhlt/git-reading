"""CLI for data enrichment operations."""

import argparse
import sys

from common.logger import get_logger
from load.db import get_adapter

from .orchestrator import EnrichmentOrchestrator
from .source_tracker import SourceTracker

logger = get_logger(__name__)


def cmd_enrich(args):
    """Run automatic enrichment from APIs."""
    logger.info("Starting enrichment...")

    with get_adapter() as adapter:
        orchestrator = EnrichmentOrchestrator(adapter)

        if args.entity_type in ("books", "both"):
            stats = orchestrator.enrich_books(limit=args.limit)
            logger.info("\nBook enrichment stats:")
            logger.info(f"  Attempted: {stats['attempted']}")
            logger.info(f"  Successful: {stats['successful']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Skipped: {stats['skipped']}")

        # TODO: Author enrichment in Phase 2
        if args.entity_type == "authors":
            logger.warning("Author enrichment not yet implemented (Phase 2)")

        orchestrator.close()


def cmd_status(args):
    """Show enrichment status and coverage."""
    with get_adapter() as adapter:
        orchestrator = EnrichmentOrchestrator(adapter)
        tracker = SourceTracker(adapter)

        # Get coverage stats
        coverage = orchestrator.get_enrichment_coverage()

        # Get enrichment stats
        enrich_stats = tracker.get_enrichment_stats()

        logger.info("\nEnrichment Status Report")
        logger.info("=" * 50)
        logger.info(f"\nBooks ({coverage['total_books']} total):")
        logger.info(
            f"  ISBN-13:            {coverage['isbn_13_count']:3d} ({coverage['isbn_13_percent']:5.1f}%)"
        )
        logger.info(
            f"  Publication Year:   {coverage['publication_year_count']:3d} ({coverage['publication_year_percent']:5.1f}%)"
        )
        logger.info(
            f"  With Subjects:      {coverage['books_with_subjects']:3d} ({coverage['subjects_percent']:5.1f}%)"
        )
        logger.info(f"  Avg Subjects/Book:  {coverage['avg_subjects_per_book']:.1f}")

        logger.info("\nEnrichment Activity:")
        logger.info(f"  Total Operations:   {enrich_stats['total_enrichments']}")

        if enrich_stats["by_source"]:
            logger.info("\n  By Source:")
            for source, count in enrich_stats["by_source"].items():
                logger.info(f"    {source:15s} {count:5d}")

        if enrich_stats["by_method"]:
            logger.info("\n  By Method:")
            for method, count in enrich_stats["by_method"].items():
                logger.info(f"    {method:15s} {count:5d}")

        orchestrator.close()


def cmd_export(args):
    """Export enrichment data for review."""
    import csv

    with get_adapter() as adapter:
        # Export books with enrichment status
        books = adapter.fetchall(
            """
            SELECT
                b.id,
                b.title,
                a.name as author,
                b.isbn_13,
                b.publication_year,
                b.openlibrary_id,
                COUNT(DISTINCT bs.subject_id) as subject_count
            FROM books b
            LEFT JOIN book_authors ba ON b.id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.id
            LEFT JOIN book_subjects bs ON b.id = bs.book_id
            GROUP BY b.id, b.title, a.name
            ORDER BY b.title
            """
        )

        if args.format == "csv":
            with open(args.output, "w", newline="", encoding="utf-8") as f:
                if not books:
                    logger.warning("No books to export")
                    return

                writer = csv.DictWriter(f, fieldnames=books[0].keys())
                writer.writeheader()
                writer.writerows(books)

            logger.info(f"Exported {len(books)} books to {args.output}")

        elif args.format == "json":
            import json

            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(books, f, indent=2, default=str)

            logger.info(f"Exported {len(books)} books to {args.output}")


def main():
    """Main entry point for the enrichment CLI."""
    parser = argparse.ArgumentParser(
        description="Enrich book and author metadata from external APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # enrich command
    enrich_parser = subparsers.add_parser(
        "enrich",
        help="Run automatic enrichment from APIs",
        description=(
            "Enrich book and author metadata from external APIs.\\n\\n"
            "Uses Open Library as the primary source for book metadata including\\n"
            "ISBNs, publication info, subjects, and cover images.\\n\\n"
            "Examples:\\n"
            "  # Enrich all unenriched books\\n"
            "  enrich-db enrich\\n\\n"
            "  # Enrich first 10 books only\\n"
            "  enrich-db enrich --limit 10\\n\\n"
            "  # Enrich with custom batch size\\n"
            "  enrich-db enrich --batch-size 20\\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    enrich_parser.add_argument(
        "--sources",
        nargs="+",
        choices=["openlibrary", "wikidata", "google"],
        default=["openlibrary"],
        help="Data sources to use (default: openlibrary)",
    )
    enrich_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of items to enrich (default: all)",
    )
    enrich_parser.add_argument(
        "--entity-type",
        choices=["books", "authors", "both"],
        default="books",
        help="Type of entity to enrich (default: books)",
    )

    # status command
    subparsers.add_parser(
        "status",
        help="Show enrichment status and coverage",
        description="Display statistics about enrichment coverage and activity.",
    )

    # export command
    export_parser = subparsers.add_parser(
        "export",
        help="Export enrichment data for review",
        description=(
            "Export enriched book data to CSV or JSON for manual review.\\n\\n"
            "Examples:\\n"
            "  # Export to CSV\\n"
            "  enrich-db export --output books.csv\\n\\n"
            "  # Export to JSON\\n"
            "  enrich-db export --output books.json --format json\\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    export_parser.add_argument("--output", required=True, help="Output file path")
    export_parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "enrich":
        cmd_enrich(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "export":
        cmd_export(args)


if __name__ == "__main__":
    main()
