"""
CLI for semantic search of reading notes.
"""

import argparse
import json
import sys
from pathlib import Path

from common.constants import VECTOR_STORE_DIR
from query.search import (
    build_search_index_from_extractions,
    search_notes,
    update_search_index_incremental,
)
from query.vector_store import VectorStore


def cmd_build(args):
    """Build the vector search index."""
    # Parse sections if provided
    sections = None
    if args.sections:
        sections = [s.strip().lower() for s in args.sections.split(",")]
        print(f"Indexing sections: {', '.join(sections)}")

    output_dir = Path(args.output)
    index_dir = Path(args.index_dir)

    if not index_dir.exists():
        print(f"Error: Index directory not found: {index_dir}")
        print("Run 'extract readings' first to create extraction files.")
        sys.exit(1)

    if args.incremental:
        # Incremental update mode
        if not output_dir.exists():
            print(f"Error: Vector store not found: {output_dir}")
            print("Run full build first (without --incremental).")
            sys.exit(1)

        update_search_index_incremental(
            index_dir=index_dir,
            vector_store_dir=output_dir,
            sections_to_index=sections,
        )

    else:
        # Full rebuild mode
        build_search_index_from_extractions(
            index_dir=index_dir,
            output_dir=output_dir,
            model_name=args.model,
            sections_to_index=sections,
        )


def cmd_search(args):
    """Search the vector index."""
    vector_store_dir = Path(args.vector_store)
    if not vector_store_dir.exists():
        print(f"Error: Vector store not found: {vector_store_dir}")
        print("Run 'search build' first to create the vector store.")
        sys.exit(1)

    results = search_notes(
        query=args.query,
        vector_store_dir=vector_store_dir,
        k=args.top_k,
        filter_author=args.author,
        filter_section=args.section,
    )

    if not results:
        print("No results found.")
        return

    # Format output
    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        # Console format
        print(f"\nFound {len(results)} result(s):\n")
        for i, result in enumerate(results, 1):
            score_percent = result["similarity"] * 100
            print(f"{i}. [{score_percent:.1f}%] {result['book_title']}")
            print(f"   by {result['author']}")
            print(f"   Section: {result['section']}")
            if result["date_read"]:
                print(f"   Read: {result['date_read']}")
            print(f"   {result['text'][:200]}...")
            if len(result["text"]) > 200:
                print(f"   [Full text: {len(result['text'])} characters]")
            print()


def cmd_stats(args):
    """Show statistics about the vector store."""
    vector_store_dir = Path(args.vector_store)
    if not vector_store_dir.exists():
        print(f"Error: Vector store not found: {vector_store_dir}")
        sys.exit(1)

    # Load model info
    model_info_path = vector_store_dir / "model_info.json"
    if model_info_path.exists():
        with open(model_info_path) as f:
            model_info = json.load(f)
        print("Model Information:")
        print(f"  Model: {model_info.get('model_name')}")
        print(f"  Dimension: {model_info.get('embedding_dimension')}")
        print(f"  Source index: {model_info.get('source_index')}")
        print(f"  Sections: {model_info.get('sections_indexed')}")
        print()

    # Load vector store
    store = VectorStore.load(vector_store_dir)
    stats = store.get_stats()

    print("Vector Store Statistics:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Total vectors: {stats['total_vectors']}")
    print(f"  Unique authors: {stats['unique_authors']}")
    print(f"  Unique books: {stats['unique_books']}")
    print(f"  Unique sections: {stats['unique_sections']}")


def main():
    """Main entry point for the search CLI."""
    parser = argparse.ArgumentParser(
        description="Semantic search for reading notes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command
    build_parser = subparsers.add_parser(
        "build",
        help="Build vector search index from extraction files",
    )

    build_parser.add_argument(
        "--index-dir",
        "-i",
        required=True,
        help="Path to directory containing extraction files",
    )
    build_parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Output directory for vector store",
    )
    build_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Apply incremental updates (requires existing vector store)",
    )
    build_parser.add_argument(
        "--model",
        "-m",
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model name (default: all-MiniLM-L6-v2)",
    )
    build_parser.add_argument(
        "--sections",
        "-s",
        help="Comma-separated list of sections to index (e.g., 'notes,excerpts')",
    )

    # Search command
    search_parser = subparsers.add_parser(
        "query",
        help="Search the vector index",
    )
    search_parser.add_argument(
        "query",
        help="Search query text",
    )
    search_parser.add_argument(
        "--vector-store",
        "-v",
        default=str(VECTOR_STORE_DIR),
        help=f"Path to vector store directory (default: {VECTOR_STORE_DIR})",
    )
    search_parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    search_parser.add_argument(
        "--author",
        "-a",
        help="Filter results by author name",
    )
    search_parser.add_argument(
        "--section",
        "-s",
        help="Filter results by section name",
    )
    search_parser.add_argument(
        "--format",
        "-f",
        choices=["console", "json"],
        default="console",
        help="Output format (default: console)",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show vector store statistics",
    )
    stats_parser.add_argument(
        "--vector-store",
        "-v",
        default=str(VECTOR_STORE_DIR),
        help=f"Path to vector store directory (default: {VECTOR_STORE_DIR})",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "build":
        cmd_build(args)
    elif args.command == "query":
        cmd_search(args)
    elif args.command == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
