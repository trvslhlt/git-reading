"""
Semantic search functionality for reading notes.

This module builds and queries a vector search index from the JSON index
created by the extract module.
"""

import json
from pathlib import Path

from common.logger import get_logger
from extract.replay import get_latest_extraction, get_new_extractions_since, replay_all_extractions
from query.embeddings import EmbeddingModel
from query.vector_store import TextNote, VectorStore

logger = get_logger(__name__)


def build_search_index(
    index_path: Path,
    output_dir: Path,
    model_name: str = "all-MiniLM-L6-v2",
):
    """
    Build a vector search index from the reading notes JSON index.

    Args:
        index_path: Path to the JSON index file (from extract)
        output_dir: Directory to save the vector store
        model_name: Name of the sentence transformer model to use
    """
    logger.info(f"Loading index from {index_path}")
    with open(index_path) as f:
        index_data = json.load(f)

    books = index_data.get("books", [])
    logger.info(f"Found [bold]{len(books)}[/bold] books in index")

    # Initialize embedding model
    model = EmbeddingModel(model_name=model_name)

    # Extract text notes
    notes: list[TextNote] = []
    texts: list[str] = []

    logger.info("Extracting text notes...")
    for book in books:
        title = book.get("title", "Unknown")
        author_first_name = book.get("author_first_name", "")
        author_last_name = book.get("author_last_name", "")
        date_read = book.get("date_read")
        source_file = book.get("source_file", "")
        sections = book.get("sections", {})

        for section_name, items in sections.items():
            for item in items:
                # Skip empty items
                if not item or not item.strip():
                    continue

                note = TextNote(
                    text=item,
                    book_title=title,
                    author_first_name=author_first_name,
                    author_last_name=author_last_name,
                    section=section_name,
                    source_file=source_file,
                    date_read=date_read,
                )
                notes.append(note)
                texts.append(item)

    logger.info(f"Extracted [bold]{len(notes)}[/bold] text notes")

    if not notes:
        logger.warning("No text notes found. Make sure your index has content in sections.")
        return

    # Generate embeddings
    logger.info("Generating embeddings...")
    embeddings = model.encode(texts, show_progress=True)

    # Create vector store
    logger.info("Building vector store...")
    store = VectorStore(dimension=model.get_dimension())
    store.add(embeddings, notes)

    # Save to disk
    output_dir = Path(output_dir)
    store.save(output_dir)

    # Save model info
    model_info = {
        "model_name": model_name,
        "embedding_dimension": model.get_dimension(),
        "source_index": str(index_path),
    }
    with open(output_dir / "model_info.json", "w") as f:
        json.dump(model_info, f, indent=2)

    logger.info("\n[green]✓[/green] Search index built successfully!")
    logger.info(f"  Model: [bold]{model_name}[/bold]")
    logger.info(f"  Notes indexed: [bold]{len(notes)}[/bold]")
    logger.info(f"  Saved to: {output_dir}")


def build_search_index_from_extractions(
    index_dir: Path,
    output_dir: Path,
    model_name: str = "all-MiniLM-L6-v2",
):
    """
    Build a vector search index from extraction files (full rebuild).

    Args:
        index_dir: Directory containing extraction files
        output_dir: Directory to save the vector store
        model_name: Name of the sentence transformer model to use
    """
    logger.info(f"Loading extraction files from {index_dir}")

    # Replay all extractions to get current state
    items = replay_all_extractions(index_dir)

    if not items:
        logger.warning(f"No items found in extraction files at {index_dir}")
        return

    logger.info(f"Found [bold]{len(items)}[/bold] items")

    # Initialize embedding model
    model = EmbeddingModel(model_name=model_name)

    # Extract text notes
    notes: list[TextNote] = []
    texts: list[str] = []

    logger.info("Extracting text notes...")
    for item in items:
        # Skip empty items
        if not item.content or not item.content.strip():
            continue

        note = TextNote(
            text=item.content,
            book_title=item.book_title,
            author_first_name=item.author_first_name,
            author_last_name=item.author_last_name,
            section=item.section,
            source_file=item.source_file,
            date_read=item.date_read,
            item_id=item.item_id,
        )
        notes.append(note)
        texts.append(item.content)

    logger.info(f"Extracted [bold]{len(notes)}[/bold] text notes")

    if not notes:
        logger.warning("No text notes found. Make sure your extractions have content.")
        return

    # Generate embeddings
    logger.info("Generating embeddings...")
    embeddings = model.encode(texts, show_progress=True)

    # Create vector store
    logger.info("Building vector store...")
    store = VectorStore(dimension=model.get_dimension())
    store.add(embeddings, notes)

    # Set checkpoint to latest extraction
    latest_extraction = get_latest_extraction(index_dir)
    if latest_extraction:
        store.set_checkpoint(latest_extraction.extraction_metadata.git_commit_hash)

    # Save to disk
    output_dir = Path(output_dir)
    store.save(output_dir)

    # Save model info
    model_info = {
        "model_name": model_name,
        "embedding_dimension": model.get_dimension(),
        "source_index_dir": str(index_dir),
    }
    with open(output_dir / "model_info.json", "w") as f:
        json.dump(model_info, f, indent=2)

    logger.info("\n[green]✓[/green] Search index built successfully!")
    logger.info(f"  Model: [bold]{model_name}[/bold]")
    logger.info(f"  Notes indexed: [bold]{len(notes)}[/bold]")
    logger.info(f"  Saved to: {output_dir}")


def update_search_index_incremental(
    index_dir: Path,
    vector_store_dir: Path,
):
    """
    Apply incremental updates to an existing vector search index.

    Args:
        index_dir: Directory containing extraction files
        vector_store_dir: Directory containing the vector store
    """
    logger.info(f"Loading vector store from {vector_store_dir}")

    # Load existing vector store
    store = VectorStore.load(vector_store_dir)

    # Get last processed commit
    last_commit = store.get_checkpoint()
    if not last_commit:
        raise ValueError("No checkpoint found in vector store. Run full build first.")

    logger.info(f"Last processed commit: {last_commit[:7]}")

    # Get new extractions since checkpoint
    new_extractions = get_new_extractions_since(index_dir, last_commit)

    if not new_extractions:
        logger.info("[green]✓[/green] No new extractions to process")
        return

    logger.info(f"Found [bold]{len(new_extractions)}[/bold] new extraction(s)")

    # Load model info
    model_info_path = vector_store_dir / "model_info.json"
    with open(model_info_path) as f:
        model_info = json.load(f)

    # Initialize embedding model
    model = EmbeddingModel(model_name=model_info["model_name"])

    # Track stats
    adds = 0
    updates = 0
    deletes = 0

    # Process each extraction
    for extraction in new_extractions:
        logger.debug(f"Processing extraction: {extraction.extraction_metadata.git_commit_hash[:7]}")

        for item in extraction.items:
            if item.operation == "add":
                # Generate embedding and add to store
                note = TextNote(
                    text=item.content,
                    book_title=item.book_title,
                    author_first_name=item.author_first_name,
                    author_last_name=item.author_last_name,
                    section=item.section,
                    source_file=item.source_file,
                    date_read=item.date_read,
                    item_id=item.item_id,
                )

                embedding = model.encode_single(item.content)
                store.add(embedding.reshape(1, -1), [note])
                adds += 1

            elif item.operation == "update":
                # For updates: mark old as deleted, add new
                # (FAISS doesn't support in-place updates)
                store.remove_by_item_id(item.item_id)

                note = TextNote(
                    text=item.content,
                    book_title=item.book_title,
                    author_first_name=item.author_first_name,
                    author_last_name=item.author_last_name,
                    section=item.section,
                    source_file=item.source_file,
                    date_read=item.date_read,
                    item_id=item.item_id,
                )

                embedding = model.encode_single(item.content)
                store.add(embedding.reshape(1, -1), [note])
                updates += 1

            elif item.operation == "delete":
                # Mark as deleted
                store.remove_by_item_id(item.item_id)
                deletes += 1

        # Update checkpoint after each extraction
        store.set_checkpoint(extraction.extraction_metadata.git_commit_hash)

    # Save updated store
    store.save(vector_store_dir)

    logger.info("\n[green]✓[/green] Incremental update complete!")
    logger.info(f"  Adds: [bold]{adds}[/bold]")
    logger.info(f"  Updates: [bold]{updates}[/bold]")
    logger.info(f"  Deletes: [bold]{deletes}[/bold]")
    logger.info(f"  Active notes: [bold]{len(store.notes) - len(store.deleted_indices)}[/bold]")
    logger.info(f"  Deleted notes: [bold]{len(store.deleted_indices)}[/bold]")


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
    for note, score in results:
        result = {
            "text": note.text,
            "similarity": score,
            "book_title": note.book_title,
            "author": note.author,
            "section": note.section,
            "source_file": note.source_file,
            "date_read": note.date_read,
        }
        formatted_results.append(result)

    return formatted_results
