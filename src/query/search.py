"""
Semantic search functionality for reading notes.

This module builds and queries a vector search index from the JSON index
created by the extract module.
"""

import json
from pathlib import Path

from common.logger import get_logger
from query.embeddings import EmbeddingModel
from query.vector_store import TextChunk, VectorStore

logger = get_logger(__name__)


def build_search_index(
    index_path: Path,
    output_dir: Path,
    model_name: str = "all-MiniLM-L6-v2",
    sections_to_index: list[str] | None = None,
):
    """
    Build a vector search index from the reading notes JSON index.

    Args:
        index_path: Path to the JSON index file (from extract)
        output_dir: Directory to save the vector store
        model_name: Name of the sentence transformer model to use
        sections_to_index: List of section names to index (e.g., ["notes", "excerpts"])
                          If None, indexes all sections
    """
    logger.info(f"Loading index from {index_path}")
    with open(index_path) as f:
        index_data = json.load(f)

    books = index_data.get("books", [])
    logger.info(f"Found [bold]{len(books)}[/bold] books in index")

    # Initialize embedding model
    model = EmbeddingModel(model_name=model_name)

    # Extract text chunks
    chunks: list[TextChunk] = []
    texts: list[str] = []

    logger.info("Extracting text chunks...")
    for book in books:
        title = book.get("title", "Unknown")
        author_first_name = book.get("author_first_name", "")
        author_last_name = book.get("author_last_name", "")
        date_read = book.get("date_read")
        source_file = book.get("source_file", "")
        sections = book.get("sections", {})

        for section_name, items in sections.items():
            # Filter by section if specified
            if sections_to_index and section_name not in sections_to_index:
                continue

            for item in items:
                # Skip empty items
                if not item or not item.strip():
                    continue

                chunk = TextChunk(
                    text=item,
                    book_title=title,
                    author_first_name=author_first_name,
                    author_last_name=author_last_name,
                    section=section_name,
                    source_file=source_file,
                    date_read=date_read,
                )
                chunks.append(chunk)
                texts.append(item)

    logger.info(f"Extracted [bold]{len(chunks)}[/bold] text chunks")

    if not chunks:
        logger.warning("No text chunks found. Make sure your index has content in sections.")
        return

    # Generate embeddings
    logger.info("Generating embeddings...")
    embeddings = model.encode(texts, show_progress=True)

    # Create vector store
    logger.info("Building vector store...")
    store = VectorStore(dimension=model.get_dimension())
    store.add(embeddings, chunks)

    # Save to disk
    output_dir = Path(output_dir)
    store.save(output_dir)

    # Save model info
    model_info = {
        "model_name": model_name,
        "embedding_dimension": model.get_dimension(),
        "source_index": str(index_path),
        "sections_indexed": sections_to_index or "all",
    }
    with open(output_dir / "model_info.json", "w") as f:
        json.dump(model_info, f, indent=2)

    logger.info("\n[green]✓[/green] Search index built successfully!")
    logger.info(f"  Model: [bold]{model_name}[/bold]")
    logger.info(f"  Chunks indexed: [bold]{len(chunks)}[/bold]")
    logger.info(f"  Saved to: {output_dir}")


def search_notes(
    query: str,
    vector_store_dir: Path,
    k: int = 5,
    filter_author: str | None = None,
    filter_section: str | None = None,
) -> list[dict]:
    """
    Search reading notes using semantic similarity.

    Args:
        query: Search query text
        vector_store_dir: Directory containing the vector store
        k: Number of results to return
        filter_author: Optional author name to filter results
        filter_section: Optional section name to filter results

    Returns:
        List of result dictionaries with text, metadata, and similarity score
    """
    # Load model info
    model_info_path = vector_store_dir / "model_info.json"
    with open(model_info_path) as f:
        model_info = json.load(f)

    # Load vector store
    logger.info(f"Loading vector store from {vector_store_dir}")
    store = VectorStore.load(vector_store_dir)

    # Initialize embedding model
    model = EmbeddingModel(model_name=model_info["model_name"])

    # Encode query
    logger.info(f'Searching for: "[bold]{query}[/bold]"')
    query_embedding = model.encode_single(query)

    # Search with pre-filtering (filtering happens inside VectorStore)
    results = store.search(
        query_embedding,
        k=k,
        filter_author=filter_author,
        filter_section=filter_section,
    )

    # Format results
    formatted_results = []
    for chunk, score in results:
        result = {
            "text": chunk.text,
            "similarity": score,
            "book_title": chunk.book_title,
            "author": chunk.author,
            "section": chunk.section,
            "source_file": chunk.source_file,
            "date_read": chunk.date_read,
        }
        formatted_results.append(result)

    return formatted_results
