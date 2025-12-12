"""
Example: Using semantic search programmatically.

This example shows how to use the search functionality from Python code,
rather than the CLI.
"""

from pathlib import Path

from common.constants import VECTOR_STORE_DIR
from query.embeddings import EmbeddingModel
from query.search import build_search_index_from_extractions, search_notes


# Example 1: Build a search index from extraction files
def build_index_example():
    """Build a search index from extraction files."""
    index_dir = Path("data/index")  # Directory containing extraction files
    output_dir = Path("data/vector_store")

    # Build the index from extraction files
    build_search_index_from_extractions(
        index_dir=index_dir,
        output_dir=output_dir,
        model_name="all-MiniLM-L6-v2",  # Fast, efficient model
    )


# Example 2: Search for content
def search_example():
    """Search for content using semantic similarity."""
    results = search_notes(
        query="mortality and death",
        vector_store_dir=Path(VECTOR_STORE_DIR),
        k=10,  # Get top 10 results
    )

    # Process results
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result['similarity']:.1%}] {result['book_title']}")
        print(f"   {result['author']}")
        print(f"   {result['text'][:100]}...")
        print()


# Example 3: Filter by author
def search_by_author_example():
    """Search within a specific author's work."""
    results = search_notes(
        query="narrative technique",
        vector_store_dir=Path(VECTOR_STORE_DIR),
        k=5,
        filter_author="John Barth",
    )

    print(f"Found {len(results)} results from John Barth")
    for result in results:
        print(f"- {result['book_title']}: {result['text'][:80]}...")


# Example 4: Use a different embedding model
def custom_model_example():
    """Use a different embedding model for higher quality."""
    index_dir = Path("data/index")
    output_dir = Path("data/vector_store_large")

    # Use a larger, more accurate model
    build_search_index_from_extractions(
        index_dir=index_dir,
        output_dir=output_dir,
        model_name="all-mpnet-base-v2",  # Higher quality, slower
    )


# Example 5: Direct embedding model usage
def embedding_example():
    """Use the embedding model directly."""
    model = EmbeddingModel("all-MiniLM-L6-v2")

    # Embed some texts
    texts = [
        "The meaning of life",
        "Existential questions",
        "Narrative structure",
    ]

    embeddings = model.encode(texts, show_progress=False)
    print(f"Generated {len(embeddings)} embeddings")
    print(f"Embedding dimension: {embeddings.shape[1]}")


if __name__ == "__main__":
    print("Semantic Search Examples")
    print("=" * 50)

    # Run examples (comment out as needed)
    # build_index_example()
    search_example()
    # search_by_author_example()
    # custom_model_example()
    # embedding_example()
