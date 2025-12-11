# Incremental Extraction Implementation Plan

## Overview

This document outlines the plan to implement incremental extraction for the git-reading system. The goal is to enable efficient processing of large datasets by only extracting changed data between runs, while maintaining a complete audit trail.

## Goals

1. **Performance**: Avoid re-processing unchanged data (simulating terrabyte-scale datasets)
2. **Auditability**: Maintain complete history of extractions via append-only log
3. **Correctness**: Track additions, updates, and deletions at the item level
4. **Portability**: Avoid system-specific features (no symlinks)
5. **Simplicity**: Prefer clean design over backward compatibility
6. **Git as Source of Truth**: Use git history for change detection and previous state retrieval

## Architecture Changes

### Current State
```
notes/
└── lastname__firstname.md

Output:
book_index.json (single file, overwritten each run)
```

### Target State
```
notes/
└── lastname__firstname.md

Output:
index/
├── extraction_20250110_143022_abc123.json    # Full extraction
├── extraction_20250110_150500_def456.json    # Incremental update
└── extraction_20250110_152000_ghi789.json    # Incremental update
```

## Data Model

### Extraction File Schema

```json
{
  "extraction_metadata": {
    "timestamp": "2025-01-10T15:20:00Z",
    "git_commit_hash": "abc123def456...",
    "git_commit_timestamp": "2025-01-10T15:15:00Z",
    "extraction_type": "full|incremental",
    "previous_commit_hash": "def456abc123...",
    "notes_directory": "/path/to/notes"
  },
  "items": [
    {
      "item_id": "sha256:abc123...",
      "operation": "add|update|delete",
      "book_title": "Book Title",
      "author_first_name": "John",
      "author_last_name": "Doe",
      "section": "notes",
      "content": "The actual note/excerpt content",
      "source_file": "doe__john.md",
      "date_read": "2024-03-15"
    }
  ]
}
```

### Item ID Generation

```python
def generate_item_id(
    book_title: str,
    author_last_name: str,
    author_first_name: str,
    section: str,
    content: str
) -> str:
    """
    Generate deterministic ID for an item.

    ID is based on: book + author + section + content
    This ensures same note in different books has different ID,
    but same note content can be tracked across versions.
    """
    canonical = f"{book_title}|{author_last_name}|{author_first_name}|{section}|{content}"
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()}"
```

### Operations

- **add**: Item did not exist in previous extraction, now present
- **update**: Item ID exists but content changed (should be rare given ID includes content)
- **delete**: Item existed in previous extraction, now absent from source file

## Implementation Tasks

### Phase 1: Core Data Structures and Utilities

#### Task 1.1: Create extraction metadata types
**File**: `src/extract/models.py` (new)

```python
@dataclass
class ExtractionMetadata:
    timestamp: str
    git_commit_hash: str
    git_commit_timestamp: str
    extraction_type: Literal["full", "incremental"]
    previous_commit_hash: str | None
    notes_directory: str

@dataclass
class ExtractedItem:
    item_id: str
    operation: Literal["add", "update", "delete"]
    book_title: str
    author_first_name: str
    author_last_name: str
    section: str
    content: str
    source_file: str
    date_read: str | None

@dataclass
class ExtractionFile:
    extraction_metadata: ExtractionMetadata
    items: list[ExtractedItem]
```

**Dependencies**: None
**Estimated Complexity**: Low

---

#### Task 1.2: Implement item ID generation
**File**: `src/extract/item_id.py` (new)

```python
def generate_item_id(
    book_title: str,
    author_last_name: str,
    author_first_name: str,
    section: str,
    content: str
) -> str:
    """Generate deterministic SHA256-based item ID."""
    pass

def validate_item_id(item_id: str) -> bool:
    """Validate item ID format (sha256:...)."""
    pass
```

**Dependencies**: None
**Tests**: Unit tests for ID generation, collision detection, format validation
**Estimated Complexity**: Low

---

#### Task 1.3: Implement extraction file naming utilities
**File**: `src/extract/file_utils.py` (new)

```python
def generate_extraction_filename(timestamp: datetime, commit_hash: str) -> str:
    """Generate filename: extraction_YYYYMMDD_HHMMSS_abc123.json"""
    pass

def parse_extraction_filename(filename: str) -> tuple[datetime, str]:
    """Parse filename to extract timestamp and commit hash."""
    pass

def find_latest_extraction(index_dir: Path) -> Path | None:
    """Find most recent extraction file by parsing all filenames."""
    pass

def list_extractions_chronological(index_dir: Path) -> list[Path]:
    """List all extraction files in chronological order."""
    pass
```

**Dependencies**: None
**Tests**: Filename generation/parsing, edge cases (empty dir, invalid files)
**Estimated Complexity**: Medium

---

#### Task 1.4: Implement extraction file I/O
**File**: `src/extract/extraction_io.py` (new)

```python
def write_extraction_file(
    file_path: Path,
    metadata: ExtractionMetadata,
    items: list[ExtractedItem]
) -> None:
    """Write extraction file with proper formatting."""
    pass

def read_extraction_file(file_path: Path) -> ExtractionFile:
    """Read and parse extraction file."""
    pass

def read_previous_commit_hash(index_dir: Path) -> str | None:
    """
    Read the most recent extraction file and return its commit hash.
    Returns None if no previous extractions exist.
    """
    pass
```

**Dependencies**: Task 1.1 (models), Task 1.3 (file_utils)
**Tests**: Round-trip I/O, reading commit hash from latest file
**Estimated Complexity**: Low

---

### Phase 2: Git Integration

#### Task 2.1: Enhanced git utilities
**File**: `src/extract/git_utils.py` (new)

```python
@dataclass
class FileChange:
    path: Path
    status: Literal["A", "M", "D"]  # Added, Modified, Deleted

def get_current_commit_hash(repo_root: Path) -> str:
    """Get current HEAD commit hash."""
    pass

def get_commit_timestamp(repo_root: Path, commit_hash: str) -> str:
    """Get ISO timestamp for a commit."""
    pass

def git_diff_files(
    repo_root: Path,
    from_commit: str,
    to_commit: str,
    pattern: str = "*.md"
) -> list[FileChange]:
    """
    Get list of changed files with their change type between two commits.
    Uses: git diff --name-status from_commit..to_commit -- *.md

    Returns list of FileChange with status:
    - "A": Added
    - "M": Modified
    - "D": Deleted
    """
    pass

def git_show_file_at_commit(
    repo_root: Path,
    commit_hash: str,
    file_path: Path
) -> str:
    """
    Get file content at specific commit.
    Uses: git show commit_hash:relative_path

    Raises FileNotFoundError if file doesn't exist at that commit.
    """
    pass
```

**Dependencies**: None (uses existing git utilities pattern from `main.py`)
**Tests**:
- Mock git commands
- Test diff detection (added, modified, deleted files)
- Test retrieving file content at previous commits
- Test handling of deleted files
**Estimated Complexity**: Medium

---

### Phase 3: Extraction Logic

#### Task 3.1: Convert book-centric to item-centric extraction
**File**: `src/extract/item_extraction.py` (new)

```python
def extract_items_from_books(
    books: list[dict],
    source_file: str
) -> list[ExtractedItem]:
    """
    Convert book-centric structure to flat list of items.

    Input: Books from parse_markdown_file()
    Output: Flat list of ExtractedItems with generated IDs
    """
    pass
```

**Dependencies**: Task 1.1 (models), Task 1.2 (item_id)
**Tests**: Convert various book structures, handle empty sections
**Estimated Complexity**: Low

---

#### Task 3.2: Implement change detection
**File**: `src/extract/change_detection.py` (new)

```python
def detect_operations_for_file(
    repo_root: Path,
    file_change: FileChange,
    previous_commit: str
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

    Returns list of items with operation field set appropriately.
    """
    pass

def compare_item_sets(
    previous_items: dict[str, ExtractedItem],
    current_items: dict[str, ExtractedItem]
) -> list[ExtractedItem]:
    """
    Helper: Compare two sets of items from the same file.

    Returns items with operations:
    - "add": In current but not in previous
    - "delete": In previous but not in current
    - "update": In both but different (rare - ID includes content)
    """
    pass
```

**Dependencies**: Task 1.1 (models), Task 2.1 (git_utils), Task 3.1 (item_extraction)
**Tests**:
- Added files (all items marked as add)
- Modified files (detect adds/updates/deletes within file)
- Deleted files (all items marked as delete)
- Edge cases (empty files, no changes)
**Estimated Complexity**: Medium

---

#### Task 3.3: Implement full extraction
**File**: `src/extract/main.py` (modify)

```python
def extract_full(
    notes_dir: Path,
    index_dir: Path,
    git_dir: Path | None
) -> Path:
    """
    Perform full extraction of all markdown files.

    1. Parse all .md files in notes_dir
    2. Convert to items
    3. Mark all as operation="add"
    4. Get current git commit info
    5. Write extraction file to index_dir

    Returns path to created extraction file.
    """
    pass
```

**Dependencies**: Tasks 1.1-1.4, 2.1, 3.1
**Tests**: Full extraction with various markdown structures
**Estimated Complexity**: Medium

---

#### Task 3.4: Implement incremental extraction
**File**: `src/extract/main.py` (modify)

```python
def extract_incremental(
    notes_dir: Path,
    index_dir: Path,
    git_dir: Path | None
) -> Path:
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

    Returns path to created extraction file.
    """
    pass
```

**Dependencies**: All previous tasks
**Tests**:
- Incremental with added files
- Incremental with modified files
- Incremental with deleted files
- Mixed changes (add + modify + delete)
- No-change scenario (should skip extraction)
**Estimated Complexity**: High

---

### Phase 4: CLI Integration

#### Task 4.1: Update CLI arguments
**File**: `src/extract/cli.py` (modify)

Replace existing CLI with new arguments:

```python
@click.command()
@click.option(
    "--notes-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing markdown notes"
)
@click.option(
    "--index-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="./index",
    help="Directory to write extraction files (default: ./index)"
)
@click.option(
    "--full",
    is_flag=True,
    default=False,
    help="Force full re-extraction (default: incremental)"
)
@click.option(
    "--git-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
    help="Git repository root (auto-detected if not specified)"
)
def main(
    notes_dir: Path,
    index_dir: Path,
    full: bool,
    git_dir: Path | None
):
    """Extract reading notes to incremental index."""
    pass
```

**Dependencies**: Tasks 3.3, 3.4
**Tests**: CLI invocation tests with various flag combinations
**Estimated Complexity**: Low
**Breaking Change**: Removes `--output` option, changes default behavior

---

### Phase 5: Testing and Documentation

#### Task 5.1: Integration tests
**File**: `tests/extract/test_incremental_extraction.py` (new)

Test scenarios:
1. First run (full extraction)
2. No changes (should skip)
3. Add new book
4. Add notes to existing book
5. Delete notes from book
6. Delete entire markdown file
7. Modify existing notes
8. Multiple incremental runs in sequence
9. Full re-extraction after incremental runs

**Dependencies**: All Phase 3 tasks
**Estimated Complexity**: High

---

#### Task 5.2: Update documentation
**Files to update**:
- `README.md`: Update extraction section with incremental examples
- `docs/ARCHITECTURE.md`: Add incremental extraction flow diagram
- `CONTRIBUTING.md`: Note new index directory structure

**Content**:
- Explain incremental vs full extraction
- Document index directory structure
- Document breaking changes from previous version
- Add examples of reading extraction history
- Update downstream consumers (search, load) to read from index directory

**Dependencies**: Implementation complete
**Estimated Complexity**: Medium
**Breaking Change**: Downstream consumers must be updated

---

## File Structure Changes

### New Files
```
src/extract/
├── models.py              # Data structures (Task 1.1)
├── item_id.py             # ID generation (Task 1.2)
├── file_utils.py          # Filename utilities (Task 1.3)
├── extraction_io.py       # File I/O (Task 1.4)
├── git_utils.py           # Git operations (Task 2.1)
├── item_extraction.py     # Book to item conversion (Task 3.1)
└── change_detection.py    # Operation detection (Task 3.2)

tests/extract/
└── test_incremental_extraction.py  # Integration tests (Task 5.1)
```

### Modified Files
```
src/extract/
├── main.py                # Extraction functions (Tasks 3.3, 3.4)
└── cli.py                 # Update CLI args (Task 4.1)

src/query/
└── search.py              # Update to read from index directory

src/load/
└── migrate_to_db.py       # Update to read from index directory
```

## Breaking Changes

This is a **breaking change** that simplifies the architecture:

### CLI Changes
- **Removed**: `--output book_index.json` option
- **New**: `--index-dir ./index` (default)
- **New**: `--full` flag for full re-extraction
- **Default behavior**: Incremental extraction (not full)

### Output Format Changes
- **Old**: Single `book_index.json` file (book-centric)
- **New**: Multiple extraction files in `index/` directory (item-centric)
- **Structure**: Append-only log with operations (add/update/delete)

### Downstream Impact
All consumers of extraction data must be updated:
- `src/query/search.py` - Read all extraction files and materialize items
- `src/load/migrate_to_db.py` - Read all extraction files and materialize items
- Any external tools reading `book_index.json`

## Migration Guide for Users

### Old Command (Removed)
```bash
extract readings --notes-dir ./notes --output book_index.json
```

### New Commands
```bash
# Incremental extraction (default)
extract readings --notes-dir ./notes --index-dir ./index

# Force full re-extraction
extract readings --notes-dir ./notes --index-dir ./index --full

# Use default index directory
extract readings --notes-dir ./notes
```

### Migration Steps
1. Run full extraction with new format: `extract readings --notes-dir ./notes --full`
2. Update downstream tools to read from `index/` directory
3. Delete old `book_index.json` file

## Testing Strategy

### Unit Tests
- ID generation (Task 1.2)
- Filename parsing (Task 1.3)
- File I/O round-trips (Task 1.4)
- Git utilities (Task 2.1)
- Change detection logic (Task 3.2)

### Integration Tests
- Full extraction end-to-end
- Incremental extraction scenarios
- No-change detection
- Deleted file handling
- Downstream consumer integration (search, load)

### Test Data
Create fixture repositories with:
- Initial state (3-4 books)
- Added books (1-2 new)
- Modified books (add/remove notes)
- Deleted files

## Performance Considerations

### Current (Full Extraction)
- Time: O(n) where n = total number of books
- Git blame calls: O(n)
- I/O: Read all .md files

### With Incremental (Git-Based)
- Time: O(m) where m = changed files
- Git operations:
  - 1 git diff --name-status call
  - m git show calls (for modified/deleted files at previous commit)
  - m git blame calls (for current files)
- I/O:
  - Read m changed .md files (current state)
  - Parse index filenames (to find latest)
  - Read 1 extraction file (to get previous commit hash)
- **No materialization needed**: Git provides previous state directly

### Key Performance Improvement
- **Before**: Required reading all previous extraction files to know what was deleted
- **After**: Git directly provides file content at previous commit
- Eliminates the O(n) materialization cost for incremental runs

### Optimization Opportunities (Future)
1. **Snapshot/Compaction**: Periodically merge extraction files for faster downstream reads
2. **Parallel processing**: Extract changed files in parallel
3. **Caching**: Cache parsed markdown to avoid re-parsing unchanged portions

## Error Handling

### Scenarios to Handle
1. **Git not available**: Fail gracefully with helpful message
2. **Corrupted extraction file**: Skip and log error, continue
3. **Invalid index directory**: Create if doesn't exist
4. **Conflicting commits**: Detect and warn if commits out of order
5. **Missing previous commit**: Fall back to full extraction

## Rollout Plan

### Step 1: Implement Core (Phases 1-3)
- Data structures, git integration, extraction logic
- Comprehensive unit tests
- No user-facing changes yet

### Step 2: Add CLI & Update Consumers (Phase 4)
- Replace CLI with new implementation
- Update downstream consumers (search, load)
- Integration testing

### Step 3: Documentation and Release (Phase 5)
- Complete documentation updates
- Document breaking changes
- Release notes highlighting incremental extraction
- Migration guide for users

## Open Questions and Decisions

### Resolved
- ✅ Use index directory instead of single file
- ✅ Item-centric model with book as metadata
- ✅ Git-based change detection (ignore uncommitted)
- ✅ Mark deleted files explicitly
- ✅ Validation handled externally
- ✅ No symlinks (portability)
- ✅ Use git as source of truth (git show for previous state, not extraction files)
- ✅ Item ID based on: book + author + section + content

### Future Considerations
- Compaction strategy (deferred)
- Downstream incremental updates (deferred to separate effort)
- Performance benchmarks with large datasets
- Handling of git repository rewrites/rebases

## Success Criteria

1. ✅ Incremental extraction faster than full for small changes
2. ✅ Complete audit trail of all extractions
3. ✅ Simple, clean architecture without backward compatibility complexity
4. ✅ Comprehensive test coverage (>90%)
5. ✅ Clear documentation and migration guide
6. ✅ Handles edge cases (deletes, renames, etc.)
7. ✅ Downstream consumers updated and working

## Estimated Timeline

- **Phase 1** (Core): 2-3 days
- **Phase 2** (Git): 1 day
- **Phase 3** (Extraction): 2-3 days
- **Phase 4** (CLI + Consumers): 1-2 days
- **Phase 5** (Testing/Docs): 2 days

**Total**: ~8-11 days of focused development

## Key Design Insights

### Git as Source of Truth
The major architectural decision is to **use git history directly** rather than reading previous extraction files:
- `git diff --name-status` tells us what changed (A/M/D)
- `git show <commit>:file` gives us previous file content
- Eliminates need for materialization logic
- Much simpler and more performant

### Item-Centric Model
Items (individual notes/excerpts) are the atomic unit:
- Books are just metadata attached to items
- Enables fine-grained tracking of additions/updates/deletions
- Natural fit for downstream vector search (items become chunks)

### Append-Only Log
Each extraction creates a new file, never modifies existing:
- Complete audit trail of all changes
- Easy to debug and replay history
- Supports time-travel queries (future enhancement)
- Downstream systems read all files and apply operations sequentially

## Notes

- This is a **breaking change** that prioritizes simplicity over backward compatibility
- The append-only log approach provides strong auditability
- Incremental extraction simulates large-scale data processing patterns (Kafka, Delta Lake)
- Future compaction can be added without changing core design
- Git integration is elegant: single source of truth for both current and historical state
- Removing backward compatibility constraints reduces complexity and development time
