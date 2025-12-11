"""Convert book-centric structure to item-centric extraction."""

from .item_id import generate_item_id
from .models import ExtractedItem


def extract_items_from_books(
    books: list[dict],
    source_file: str,
    operation: str = "add",
) -> list[ExtractedItem]:
    """
    Convert book-centric structure to flat list of items.

    Args:
        books: Books from parse_markdown_file()
        source_file: Source markdown filename
        operation: Operation type ("add", "update", or "delete")

    Returns:
        Flat list of ExtractedItems with generated IDs
    """
    items: list[ExtractedItem] = []

    for book in books:
        book_title = book["title"]
        author_first_name = book.get("author_first_name", "")
        author_last_name = book.get("author_last_name", "")
        date_read = book.get("date_read")

        # Process each section
        sections = book.get("sections", {})
        for section_name, section_items in sections.items():
            for content in section_items:
                # Generate deterministic ID
                item_id = generate_item_id(
                    book_title=book_title,
                    author_last_name=author_last_name,
                    author_first_name=author_first_name,
                    section=section_name,
                    content=content,
                )

                item = ExtractedItem(
                    item_id=item_id,
                    operation=operation,  # type: ignore
                    book_title=book_title,
                    author_first_name=author_first_name,
                    author_last_name=author_last_name,
                    section=section_name,
                    content=content,
                    source_file=source_file,
                    date_read=date_read,
                )

                items.append(item)

    return items
