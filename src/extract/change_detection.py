"""Change detection for incremental extraction."""

from pathlib import Path

from common.logger import get_logger

from .git_utils import FileChange, git_show_file_at_commit
from .item_extraction import extract_items_from_books
from .models import ExtractedItem

logger = get_logger(__name__)


def detect_operations_for_file(
    repo_root: Path,
    file_change: FileChange,
    previous_commit: str,
    parse_markdown_func,
) -> list[ExtractedItem]:
    """
    Detect operations (add/update/delete) for a single changed file.

    For added files ("A"):
    - Extract items from current file
    - Mark all as "add"

    For modified files ("M"):
    - Extract items from current file
    - Extract items from previous commit (git show)
    - Compare: mark as "add", "update", or "delete"

    For deleted files ("D"):
    - Extract items from previous commit (git show)
    - Mark all as "delete"

    Args:
        repo_root: Path to git repository root
        file_change: FileChange object with path and status
        previous_commit: Previous commit hash for comparison
        parse_markdown_func: Function to parse markdown files

    Returns:
        List of items with operation field set appropriately
    """
    if file_change.status == "A":
        # Added file: extract current and mark all as "add"
        logger.info(f"File added: {file_change.path.name}")
        books = parse_markdown_func(file_change.path, repo_root)
        return extract_items_from_books(books, file_change.path.name, operation="add")

    elif file_change.status == "D":
        # Deleted file: extract previous and mark all as "delete"
        logger.info(f"File deleted: {file_change.path.name}")
        try:
            # Get file content at previous commit
            previous_content = git_show_file_at_commit(repo_root, previous_commit, file_change.path)

            # Write to temporary file and parse
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(previous_content)
                tmp_path = Path(tmp.name)

            try:
                # Parse using same filename for author extraction
                # but read from temp file
                original_name = file_change.path.name
                tmp_path_with_name = tmp_path.parent / original_name
                tmp_path.rename(tmp_path_with_name)

                books = parse_markdown_func(tmp_path_with_name, repo_root)
                return extract_items_from_books(books, original_name, operation="delete")
            finally:
                # Clean up temp file
                if tmp_path_with_name.exists():
                    tmp_path_with_name.unlink()
                elif tmp_path.exists():
                    tmp_path.unlink()

        except FileNotFoundError:
            logger.warning(f"Could not find previous version of {file_change.path.name}")
            return []

    elif file_change.status == "M":
        # Modified file: compare previous and current
        logger.info(f"File modified: {file_change.path.name}")

        # Extract current items
        current_books = parse_markdown_func(file_change.path, repo_root)
        current_items = extract_items_from_books(
            current_books, file_change.path.name, operation="add"
        )
        current_items_dict = {item.item_id: item for item in current_items}

        # Extract previous items
        previous_items_dict = {}
        try:
            previous_content = git_show_file_at_commit(repo_root, previous_commit, file_change.path)

            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(previous_content)
                tmp_path = Path(tmp.name)

            try:
                original_name = file_change.path.name
                tmp_path_with_name = tmp_path.parent / original_name
                tmp_path.rename(tmp_path_with_name)

                previous_books = parse_markdown_func(tmp_path_with_name, repo_root)
                previous_items = extract_items_from_books(
                    previous_books, original_name, operation="delete"
                )
                previous_items_dict = {item.item_id: item for item in previous_items}
            finally:
                if tmp_path_with_name.exists():
                    tmp_path_with_name.unlink()
                elif tmp_path.exists():
                    tmp_path.unlink()

        except FileNotFoundError:
            logger.warning(
                f"Could not find previous version of {file_change.path.name}, treating as all new"
            )

        # Compare and determine operations
        return compare_item_sets(previous_items_dict, current_items_dict)

    return []


def compare_item_sets(
    previous_items: dict[str, ExtractedItem],
    current_items: dict[str, ExtractedItem],
) -> list[ExtractedItem]:
    """
    Helper: Compare two sets of items from the same file.

    Returns items with operations:
    - "add": In current but not in previous
    - "delete": In previous but not in current
    - "update": In both but different (rare - ID includes content)

    Args:
        previous_items: Dict of item_id -> ExtractedItem from previous version
        current_items: Dict of item_id -> ExtractedItem from current version

    Returns:
        List of items with appropriate operations
    """
    operations: list[ExtractedItem] = []

    # Find additions (in current, not in previous)
    for item_id, item in current_items.items():
        if item_id not in previous_items:
            # New item
            item.operation = "add"
            operations.append(item)
        else:
            # Item exists in both - check if content changed
            # Since item_id includes content, this should be rare
            # But we check anyway in case of hash collisions or metadata changes
            prev_item = previous_items[item_id]
            if (
                item.content != prev_item.content
                or item.book_title != prev_item.book_title
                or item.section != prev_item.section
            ):
                item.operation = "update"
                operations.append(item)
            # else: no change, don't include

    # Find deletions (in previous, not in current)
    for item_id, item in previous_items.items():
        if item_id not in current_items:
            item.operation = "delete"
            operations.append(item)

    return operations
