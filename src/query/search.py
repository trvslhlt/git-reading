"""
Semantic search functionality for reading notes.

This module builds and queries a vector search index from the JSON index
created by the extract module.
"""

import json
from pathlib import Path

from query.embeddings import EmbeddingModel
from query.vector_store import TextChunk, VectorStore


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
    print(f"Loading index from {index_path}")
    with open(index_path) as f:
        index_data = json.load(f)

    books = index_data.get("books", [])
    print(f"Found {len(books)} books in index")

    # Initialize embedding model
    model = EmbeddingModel(model_name=model_name)

    # Extract text chunks
    chunks: list[TextChunk] = []
    texts: list[str] = []

    print("Extracting text chunks...")
    for book in books:
        title = book.get("title", "Unknown")
        author = book.get("author", "Unknown")
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
                    author=author,
                    section=section_name,
                    source_file=source_file,
                    date_read=date_read,
                )
                chunks.append(chunk)
                texts.append(item)

    print(f"Extracted {len(chunks)} text chunks")

    if not chunks:
        print("No text chunks found. Make sure your index has content in sections.")
        return

    # Generate embeddings
    print("Generating embeddings...")
    embeddings = model.encode(texts, show_progress=True)

    # Create vector store
    print("Building vector store...")
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

    print("\n✓ Search index built successfully!")
    print(f"  Model: {model_name}")
    print(f"  Chunks indexed: {len(chunks)}")
    print(f"  Saved to: {output_dir}")


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
    print(f"Loading vector store from {vector_store_dir}")
    store = VectorStore.load(vector_store_dir)

    # Initialize embedding model
    model = EmbeddingModel(model_name=model_info["model_name"])

    # Encode query
    print(f'Searching for: "{query}"')
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
