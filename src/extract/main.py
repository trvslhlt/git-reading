"""
Index reading notes into a queryable JSON structure.

Scans markdown files, parses book titles and sections, and uses git history
to determine when each book was read (based on when the title was added).
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from common.constants import CANONICAL_SECTIONS
from common.logger import get_logger

from .change_detection import detect_operations_for_file
from .extraction_io import read_previous_commit_hash, write_extraction_file
from .file_utils import generate_extraction_filename
from .git_utils import get_commit_timestamp, get_current_commit_hash, git_diff_files
from .item_extraction import extract_items_from_books
from .models import ExtractionMetadata

logger = get_logger(__name__)


def get_git_date_for_line(filepath: Path, line_content: str, repo_root: Path) -> str | None:
    """
    Use git blame to find when a specific line was added.
    Returns ISO date string or None if not in git history.
    """
    try:
        # Get relative path from repo root
        rel_path = filepath.relative_to(repo_root)

        # Run git blame with porcelain format for easy parsing
        result = subprocess.run(
            [
                "git",
                "blame",
                "--porcelain",
                "-L",
                f"/{re.escape(line_content)}/",
                "--",
                str(rel_path),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        # Parse the porcelain output for author-time
        for line in result.stdout.split("\n"):
            if line.startswith("author-time "):
                timestamp = int(line.split(" ")[1])
                return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

        return None
    except Exception:
        return None


def find_git_root(start_path: Path) -> Path | None:
    """Find the git repository root from a starting path."""
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


def author_from_filename(filename: str) -> tuple[str, str]:
    """
    Convert filename to author first and last names.
    e.g., 'le_guin__ursula_k.md' -> ('Ursula K', 'Le Guin')
    e.g., 'barth__john.md' -> ('John', 'Barth')

    Format: last_name__first_name.md (double underscore separator)
    Single underscores within names become spaces.

    Returns:
        tuple[str, str]: (first_name, last_name)
    """
    stem = Path(filename).stem  # Remove .md

    # Split on double underscore to separate last name from first name
    if "__" in stem:
        parts = stem.split("__")
        if len(parts) == 2:
            last_name, first_name = parts
            # Replace single underscores with spaces and capitalize each word
            last_parts = [p.capitalize() for p in last_name.split("_")]
            first_parts = [p.capitalize() for p in first_name.split("_")]
            # Return as tuple (first_name, last_name)
            return (" ".join(first_parts), " ".join(last_parts))

    # Fallback: treat single underscores as word separators, assume all is last name
    parts = stem.split("_")
    full_name = " ".join(part.capitalize() for part in parts)
    return ("", full_name)


def parse_markdown_file(filepath: Path, repo_root: Path | None) -> list[dict]:
    """
    Parse a markdown file and extract all books with their sections.
    Returns a list of book dictionaries.
    """
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    author_first_name, author_last_name = author_from_filename(filepath.name)
    books = []
    current_book = None
    current_section = None
    current_section_items = []

    def save_current_section():
        """Save the current section to the current book."""
        nonlocal current_section, current_section_items
        if current_book and current_section:
            if current_section_items:
                section_key = current_section.lower().strip()
                current_book["sections"][section_key] = current_section_items
            else:
                # Log error for empty section
                logger.error(
                    f"[red]✗[/red] Empty section in {filepath.name}: "
                    f'"{current_book["title"]}" > "{current_section}"'
                )
        current_section = None
        current_section_items = []

    def save_current_book():
        """Save the current book to the books list."""
        nonlocal current_book
        save_current_section()
        if current_book:
            # Check if book has any sections
            if not current_book["sections"]:
                logger.error(
                    f"[red]✗[/red] Book with no sections in {filepath.name}: "
                    f'"{current_book["title"]}"'
                )
            books.append(current_book)
        current_book = None

    for line in lines:
        # Check for book title (# Title)
        if line.startswith("# ") and not line.startswith("## "):
            potential_title = line[2:].strip()

            # Skip if this looks like a section name, not a book title
            if potential_title.lower() in CANONICAL_SECTIONS:
                # Treat it as a section under the current book
                save_current_section()
                current_section = potential_title
                current_section_items = []
                continue

            save_current_book()
            title = potential_title

            # Get git date for this book
            date_read = None
            if repo_root:
                date_read = get_git_date_for_line(filepath, line, repo_root)

            current_book = {
                "title": title,
                "author_first_name": author_first_name,
                "author_last_name": author_last_name,
                "date_read": date_read,
                "source_file": filepath.name,
                "sections": {},
            }

        # Check for section header (## Section)
        elif line.startswith("## "):
            save_current_section()
            current_section = line[3:].strip()
            current_section_items = []

        # Content line (could be a list item or paragraph)
        elif current_book and current_section:
            stripped = line.strip()
            if stripped:
                # Check if this is indented content (should be grouped with parent)
                if line.startswith("    ") and current_section_items:
                    # This is an indented line (nested content)
                    # Append to the last item with a newline to preserve structure
                    current_section_items[-1] += "\n" + stripped
                # Handle top-level list items
                elif stripped.startswith("- "):
                    # This is a top-level list item
                    current_section_items.append(stripped[2:])
                else:
                    # Non-list content
                    current_section_items.append(stripped)

    # Don't forget the last book/section
    save_current_book()

    return books


def index_notes(notes_dir: Path, output_path: Path, git_dir: Path | None = None):
    """
    Scan all markdown files and build the index.

    Args:
        notes_dir: Directory containing markdown notes
        output_path: Path to write the JSON index
        git_dir: Git repository directory (if None, will search from notes_dir)
    """
    notes_dir = notes_dir.resolve()

    # Determine git repository root
    if git_dir:
        repo_root = git_dir.resolve()
        if not (repo_root / ".git").exists():
            logger.warning(f"{repo_root} does not appear to be a git repository")
            logger.warning("Date information will not be available.")
            repo_root = None
    else:
        repo_root = find_git_root(notes_dir)
        if not repo_root:
            logger.warning(f"No git repository found at or above {notes_dir}")
            logger.warning("Date information will not be available.")

    all_books = []
    md_files = sorted(notes_dir.glob("*.md"))

    if not md_files:
        logger.warning(f"No markdown files found in {notes_dir}")
        return

    logger.info(f"Found [bold]{len(md_files)}[/bold] markdown file(s)")

    for md_file in md_files:
        logger.debug(f"Parsing {md_file.name}...")
        books = parse_markdown_file(md_file, repo_root)
        all_books.extend(books)
        logger.debug(f"  Found {len(books)} book(s)")

    # Sort by date_read (None values at end)
    all_books.sort(key=lambda b: (b["date_read"] is None, b["date_read"] or ""))

    index = {
        "generated_at": datetime.now().isoformat(),
        "notes_directory": str(notes_dir),
        "total_books": len(all_books),
        "books": all_books,
    }

    output_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        f"[green]✓[/green] Wrote index with [bold]{len(all_books)}[/bold] books to {output_path}"
    )


def extract_full(
    notes_dir: Path,
    index_dir: Path,
    git_dir: Path | None,
) -> Path:
    """
    Perform full extraction of all markdown files.

    1. Parse all .md files in notes_dir
    2. Convert to items
    3. Mark all as operation="add"
    4. Get current git commit info
    5. Write extraction file to index_dir

    Args:
        notes_dir: Directory containing markdown notes
        index_dir: Directory to write extraction files
        git_dir: Git repository directory (if None, will search from notes_dir)

    Returns:
        Path to created extraction file

    Raises:
        ValueError: If git repository not found or index directory not empty
    """
    notes_dir = notes_dir.resolve()

    # Check if index directory has existing extraction files
    if index_dir.exists():
        existing_files = list(index_dir.glob("extraction_*.json"))
        if existing_files:
            raise ValueError(
                f"Index directory '{index_dir}' already contains {len(existing_files)} extraction file(s). "
                "Full extraction requires an empty index directory to avoid overwriting history. "
                "Either delete the existing files or use a different directory."
            )

    # Determine git repository root
    if git_dir:
        repo_root = git_dir.resolve()
    else:
        repo_root = find_git_root(notes_dir)

    if not repo_root or not (repo_root / ".git").exists():
        raise ValueError("Git repository required for extraction")

    # Get current commit info
    current_commit = get_current_commit_hash(repo_root)
    commit_timestamp = get_commit_timestamp(repo_root, current_commit)

    logger.info(f"Performing full extraction at commit {current_commit[:7]}")

    # Find all markdown files
    md_files = sorted(notes_dir.glob("*.md"))

    if not md_files:
        logger.warning(f"No markdown files found in {notes_dir}")
        return None

    logger.info(f"Found [bold]{len(md_files)}[/bold] markdown file(s)")

    # Extract all items
    all_items = []
    for md_file in md_files:
        logger.debug(f"Parsing {md_file.name}...")
        books = parse_markdown_file(md_file, repo_root)
        items = extract_items_from_books(books, md_file.name, operation="add")
        all_items.extend(items)
        logger.debug(f"  Found {len(items)} item(s)")

    # Create extraction metadata
    metadata = ExtractionMetadata(
        timestamp=datetime.now().isoformat(),
        git_commit_hash=current_commit,
        git_commit_timestamp=commit_timestamp,
        extraction_type="full",
        previous_commit_hash=None,
        notes_directory=str(notes_dir),
    )

    # Generate filename and write
    filename = generate_extraction_filename(datetime.now(), current_commit)
    output_path = index_dir / filename

    write_extraction_file(output_path, metadata, all_items)

    logger.info(
        f"[green]✓[/green] Wrote full extraction with [bold]{len(all_items)}[/bold] items to {output_path.name}"
    )

    return output_path


def extract_incremental(
    notes_dir: Path,
    index_dir: Path,
    git_dir: Path | None,
) -> Path | None:
    """
    Perform incremental extraction using git as source of truth.

    1. Find latest extraction file in index_dir
    2. Load previous commit hash from that file
    3. Get current commit hash
    4. Run git diff --name-status to find changed files (A/M/D)
    5. If no changes, return early (no new extraction file)
    6. For each changed file:
       - If added ("A"): extract current, mark all as "add"
       - If modified ("M"): extract current + previous (git show), compare
       - If deleted ("D"): extract previous (git show), mark all as "delete"
    7. Collect all operations from all files
    8. Write new extraction file

    Args:
        notes_dir: Directory containing markdown notes
        index_dir: Directory containing extraction files
        git_dir: Git repository directory (if None, will search from notes_dir)

    Returns:
        Path to created extraction file, or None if no changes

    Raises:
        ValueError: If git repository not found or no previous extraction exists
    """
    notes_dir = notes_dir.resolve()

    # Determine git repository root
    if git_dir:
        repo_root = git_dir.resolve()
    else:
        repo_root = find_git_root(notes_dir)

    if not repo_root or not (repo_root / ".git").exists():
        raise ValueError("Git repository required for extraction")

    # Find previous extraction
    previous_commit = read_previous_commit_hash(index_dir)

    if previous_commit is None:
        logger.info("No previous extraction found, performing full extraction")
        return extract_full(notes_dir, index_dir, git_dir)

    # Get current commit
    current_commit = get_current_commit_hash(repo_root)
    commit_timestamp = get_commit_timestamp(repo_root, current_commit)

    logger.info(f"Incremental extraction: {previous_commit[:7]} → {current_commit[:7]}")

    # Find changed files
    changed_files = git_diff_files(repo_root, previous_commit, current_commit, "*.md")

    if not changed_files:
        logger.info("[green]✓[/green] No changes detected, skipping extraction")
        return None

    logger.info(f"Found {len(changed_files)} changed file(s)")

    # Process each changed file
    all_items = []
    for file_change in changed_files:
        # Get relative path for logging
        try:
            rel_path = file_change.path.relative_to(notes_dir)
            log_path = str(rel_path)
        except ValueError:
            log_path = file_change.path.name

        logger.debug(f"Processing {file_change.status}: {log_path}")

        items = detect_operations_for_file(
            repo_root, file_change, previous_commit, parse_markdown_file
        )
        all_items.extend(items)

        logger.debug(f"  {len(items)} operation(s)")

    # Create extraction metadata
    metadata = ExtractionMetadata(
        timestamp=datetime.now().isoformat(),
        git_commit_hash=current_commit,
        git_commit_timestamp=commit_timestamp,
        extraction_type="incremental",
        previous_commit_hash=previous_commit,
        notes_directory=str(notes_dir),
    )

    # Generate filename and write
    filename = generate_extraction_filename(datetime.now(), current_commit)
    output_path = index_dir / filename

    write_extraction_file(output_path, metadata, all_items)

    # Log summary by operation type
    adds = sum(1 for item in all_items if item.operation == "add")
    updates = sum(1 for item in all_items if item.operation == "update")
    deletes = sum(1 for item in all_items if item.operation == "delete")

    logger.info(
        f"[green]✓[/green] Wrote incremental extraction to {output_path.name}: "
        f"{adds} adds, {updates} updates, {deletes} deletes"
    )

    return output_path
