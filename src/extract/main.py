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
        if current_book and current_section and current_section_items:
            section_key = current_section.lower().strip()
            current_book["sections"][section_key] = current_section_items
        current_section = None
        current_section_items = []

    def save_current_book():
        """Save the current book to the books list."""
        nonlocal current_book
        save_current_section()
        if current_book:
            books.append(current_book)
        current_book = None

    # Section names that shouldn't be treated as book titles
    section_names = {
        "terms",
        "notes",
        "excerpts",
        "threads",
        "ideas",
        "representations",
        "images",
        "same time",
        "thread",
        "note",
        "excerpt",
        "term",
    }

    for line in lines:
        # Check for book title (# Title)
        if line.startswith("# ") and not line.startswith("## "):
            potential_title = line[2:].strip()

            # Skip if this looks like a section name, not a book title
            if potential_title.lower() in section_names:
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
            print(f"Warning: {repo_root} does not appear to be a git repository")
            print("Date information will not be available.")
            repo_root = None
    else:
        repo_root = find_git_root(notes_dir)
        if not repo_root:
            print(f"Warning: No git repository found at or above {notes_dir}")
            print("Date information will not be available.")

    all_books = []
    md_files = sorted(notes_dir.glob("*.md"))

    if not md_files:
        print(f"No markdown files found in {notes_dir}")
        return

    print(f"Found {len(md_files)} markdown file(s)")

    for md_file in md_files:
        print(f"  Parsing {md_file.name}...")
        books = parse_markdown_file(md_file, repo_root)
        all_books.extend(books)
        print(f"    Found {len(books)} book(s)")

    # Sort by date_read (None values at end)
    all_books.sort(key=lambda b: (b["date_read"] is None, b["date_read"] or ""))

    index = {
        "generated_at": datetime.now().isoformat(),
        "notes_directory": str(notes_dir),
        "total_books": len(all_books),
        "books": all_books,
    }

    output_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote index with {len(all_books)} books to {output_path}")
