# Incremental Load Fix: Book Title Changes

## Problem

When a book title is corrected in the source markdown files (e.g., fixing "Homegoing" to "Housekeeping"), the incremental load process created **orphaned book records**:

1. ✅ New book record created with correct title
2. ✅ Notes updated to point to new book
3. ❌ **Old book record left in database** with incorrect title
4. ❌ **book_authors entries** for old book remained
5. ❌ **book_subjects entries** for old book remained (if enriched)

### Example Issue

```
Before fix in markdown:    "Homegoing" by Marilynne Robinson (typo)
After fix in markdown:     "Housekeeping" by Marilynne Robinson (correct)

After incremental load:
- Database has BOTH "Homegoing" and "Housekeeping" by Robinson
- Notes point to "Housekeeping" (correct)
- "Homegoing" book is orphaned (has no notes)
- Query for "Homegoing" returns incorrect book
```

## Root Cause

In [src/load/load_data.py](src/load/load_data.py), the `load_incremental()` function's update operation (lines 294-304) only updated the **note** record but not the **book_id**:

```python
# OLD CODE (BUGGY):
elif item.operation == "update":
    # Update existing note
    adapter.execute(
        """
        UPDATE notes
        SET section = ?, excerpt = ?
        WHERE item_id = ?
    """,
        (item.section, item.content, item.item_id),
    )
```

When the title changed:
- `book_id` changed (it's generated from `title + author`)
- New book was created on next add operation
- Old book remained in database with no notes pointing to it

## Solution

### Part 1: Update book_id on note updates

Now when updating a note, we:
1. Ensure the new book record exists
2. Ensure the new book_author link exists
3. **Update the note's book_id** to point to the new book

```python
# NEW CODE (FIXED):
elif item.operation == "update":
    # Ensure author exists (in case name changed)
    adapter.execute(
        """
        INSERT INTO authors (id, first_name, last_name, name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO NOTHING
    """,
        (author_id, item.author_first_name, item.author_last_name, author),
    )

    # Ensure book exists (in case title changed)
    adapter.execute(
        """
        INSERT INTO books (id, title)
        VALUES (?, ?)
        ON CONFLICT(id) DO NOTHING
    """,
        (book_id, item.book_title),
    )

    # Link book to author (in case relationship changed)
    adapter.execute(
        """
        INSERT INTO book_authors (book_id, author_id)
        VALUES (?, ?)
        ON CONFLICT DO NOTHING
    """,
        (book_id, author_id),
    )

    # Update existing note (including book_id in case title changed)
    adapter.execute(
        """
        UPDATE notes
        SET book_id = ?, section = ?, excerpt = ?
        WHERE item_id = ?
    """,
        (book_id, item.section, item.content, item.item_id),
    )
```

### Part 2: Cleanup orphaned records

After processing all incremental updates, we now clean up orphaned records in the correct order (respecting foreign keys):

```python
# Clean up orphaned records after all updates
logger.debug("Cleaning up orphaned records...")

# 1. Delete orphaned book_subjects (foreign key to books)
adapter.execute(
    """
    DELETE FROM book_subjects
    WHERE book_id NOT IN (SELECT id FROM books)
    """
)

# 2. Delete orphaned book_authors (orphaned by book deletion)
adapter.execute(
    """
    DELETE FROM book_authors
    WHERE book_id NOT IN (SELECT id FROM books)
    """
)

# 3. Delete orphaned books (books with no notes)
adapter.execute(
    """
    DELETE FROM books
    WHERE id NOT IN (SELECT DISTINCT book_id FROM notes)
    """
)

# 4. Delete orphaned authors (authors with no books)
adapter.execute(
    """
    DELETE FROM authors
    WHERE id NOT IN (SELECT DISTINCT author_id FROM book_authors)
    """
)

# 5. Delete orphaned subjects (subjects with no books)
adapter.execute(
    """
    DELETE FROM subjects
    WHERE id NOT IN (SELECT DISTINCT subject_id FROM book_subjects)
    """
)
```

## Benefits

1. **No more duplicates**: Only one book record per unique title+author combination
2. **Automatic cleanup**: Orphaned records are automatically removed
3. **Handles edge cases**:
   - Book title changes
   - Author name changes
   - Book-author relationship changes
   - Enrichment data cleanup (subjects)

## Testing

To test the fix:

1. **Create a book with a typo**:
   ```markdown
   # Homegoing
   **Marilynne Robinson**

   Some notes...
   ```

2. **Run extraction and load**:
   ```bash
   make run-extract ARGS='--notes-dir readings'
   make run-load ARGS='--index-dir ./data/index'
   ```

3. **Fix the typo**:
   ```markdown
   # Housekeeping  # Fixed!
   **Marilynne Robinson**

   Some notes...
   ```

4. **Run incremental update**:
   ```bash
   make run-extract ARGS='--notes-dir readings'
   make run-load ARGS='--index-dir ./data/index --incremental'
   ```

5. **Verify cleanup**:
   ```sql
   -- Should return only 1 book
   SELECT COUNT(*) FROM books
   WHERE title IN ('Homegoing', 'Housekeeping');

   -- Should return 'Housekeeping'
   SELECT title FROM books
   WHERE title LIKE '%keeping%';

   -- Should return 0 orphans
   SELECT COUNT(*) FROM books
   WHERE id NOT IN (SELECT DISTINCT book_id FROM notes);
   ```

## Files Modified

- [`src/load/load_data.py`](src/load/load_data.py) - Lines 294-403
  - Updated `load_incremental()` function
  - Added book_id update to note updates
  - Added orphaned record cleanup

## Related Issues

- Fixes the "Homegoing" / "Housekeeping" duplicate issue
- Prevents future duplicates from title/author corrections
- Maintains database integrity with foreign key constraints
