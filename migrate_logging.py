#!/usr/bin/env python3
"""Script to migrate print statements to logging across the codebase."""

import re
from pathlib import Path


def migrate_file(file_path: Path) -> bool:
    """Migrate a single file from print to logging.

    Returns:
        True if file was modified, False otherwise
    """
    content = file_path.read_text()
    original = content

    # Check if already has logger import
    has_logger = "from common.logger import get_logger" in content
    has_logger_instance = re.search(r"^logger = get_logger\(__name__\)", content, re.MULTILINE)

    if not has_logger:
        # Add import after other imports
        import_pattern = r"(from pathlib import Path\n|import .*\n)"
        matches = list(re.finditer(import_pattern, content))
        if matches:
            last_import = matches[-1]
            insert_pos = last_import.end()
            content = (
                content[:insert_pos]
                + "\nfrom common.logger import get_logger\n"
                + content[insert_pos:]
            )

    if not has_logger_instance:
        # Add logger instance after imports
        # Find the last import or the docstring end
        pattern = r'(""".*?"""|\'\'\'.*?\'\'\')\n\n'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            insert_pos = match.end()
            content = (
                content[:insert_pos] + "logger = get_logger(__name__)\n\n" + content[insert_pos:]
            )

    # Replace print statements
    # Simple case: print("message")
    content = re.sub(r'print\("(.+?)"\)', r'logger.info("\1")', content)

    # f-string case: print(f"message {var}")
    content = re.sub(r'print\(f"(.+?)"\)', r'logger.info(f"\1")', content)

    # Add rich markup to numbers and important info
    content = re.sub(
        r'logger\.info\(f"(.+?)\{(\w+)\}(.+?)"\)', r'logger.info(f"\1[bold]{\2}[/bold]\3")', content
    )

    if content != original:
        file_path.write_text(content)
        return True
    return False


def main():
    """Migrate all Python files in src/ directory."""
    src_dir = Path("src")
    modified_files = []

    for py_file in src_dir.rglob("*.py"):
        # Skip __init__.py files and already migrated files
        if py_file.name == "__init__.py":
            continue
        if "common/logger.py" in str(py_file):
            continue
        if "extract/main.py" in str(py_file):
            continue  # Already migrated
        if "load/migrate_to_db.py" in str(py_file):
            continue  # Already migrated

        try:
            if migrate_file(py_file):
                modified_files.append(py_file)
                print(f"✓ Migrated {py_file}")
        except Exception as e:
            print(f"✗ Error migrating {py_file}: {e}")

    print(f"\nMigrated {len(modified_files)} files")


if __name__ == "__main__":
    main()
