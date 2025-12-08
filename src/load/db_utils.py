def generate_author(first_name, last_name):
    """Generate author name from first and last name.

    Args:
        first_name: First name
        last_name: Last name
    Returns:
        Full author name
    """
    author = "Unknown"
    if first_name and last_name:
        author = f"{first_name} {last_name}"
    elif last_name:
        author = last_name
    elif first_name:
        author = first_name
    return author


def _generate_id(name: str) -> str:
    """Generate a stable ID from name.

    Args:
        name: Name string
    Returns:
        Stable ID
    """
    slug = name.lower()
    # Remove non-alphanumeric except spaces, hyphens, underscores
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in slug)
    # Split on whitespace and join with hyphens (normalizes multiple spaces too)
    slug = "-".join(slug.split())
    return slug[:100]


def generate_author_id(author: str) -> str:
    """Generate a stable author ID from author.

    Args:
        author: Author name

    Returns:
        Stable author ID
    """
    return _generate_id(author)


def generate_book_id(title: str, author: str) -> str:
    """Generate a stable book ID from title and author.

    Args:
        title: Book title
        author: Book author

    Returns:
        Stable book ID (format: title-slug_author-slug, max 100 chars)
    """
    # Generate separate slugs for title and author
    return _generate_id(f"{title}_{author}")
