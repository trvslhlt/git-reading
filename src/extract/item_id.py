"""Item ID generation utilities."""

import hashlib
import re


def generate_item_id(
    book_title: str,
    author_last_name: str,
    author_first_name: str,
    section: str,
    content: str,
) -> str:
    """
    Generate deterministic SHA256-based item ID.

    ID is based on: book + author + section + content.
    This ensures same note in different books has different ID,
    but same note content can be tracked across versions.

    Args:
        book_title: Title of the book
        author_last_name: Author's last name
        author_first_name: Author's first name
        section: Section name (e.g., "notes", "excerpts")
        content: The actual content of the item

    Returns:
        SHA256 hash prefixed with "sha256:"
    """
    # Create canonical representation
    canonical = f"{book_title}|{author_last_name}|{author_first_name}|{section}|{content}"

    # Generate hash
    hash_obj = hashlib.sha256(canonical.encode("utf-8"))
    return f"sha256:{hash_obj.hexdigest()}"


def validate_item_id(item_id: str) -> bool:
    """
    Validate item ID format.

    Args:
        item_id: Item ID to validate

    Returns:
        True if valid, False otherwise
    """
    # Must match: sha256:<64 hex characters>
    pattern = r"^sha256:[0-9a-f]{64}$"
    return bool(re.match(pattern, item_id))
