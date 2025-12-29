# Known Issues

## Critical: PostgreSQL Transaction Not Rolled Back on Error (RESOLVED)

**Status**: Fixed
**Date Fixed**: 2025-12-29
**Severity**: High (was)
**Affects**: PostgreSQL adapter only (SQLite unaffected)

### Problem

When a database error occurs during enrichment, the PostgreSQL adapter raises a `DatabaseError` exception but does not roll back the transaction. This leaves PostgreSQL in an "aborted transaction" state where all subsequent commands fail with:

```
ERROR: current transaction is aborted, commands ignored until end of transaction block
```

### Root Cause

In `src/load/db/postgres_adapter.py`, the `execute()` method (lines 237-259) catches `psycopg.Error` exceptions and raises `DatabaseError`, but does not call `self._conn.rollback()` before raising.

```python
# Line 256-259 (current buggy code)
except psycopg.errors.IntegrityError as e:
    raise DBIntegrityError(f"Integrity constraint violation: {e}") from e
except psycopg.Error as e:
    raise DatabaseError(f"Query execution failed: {e}") from e
    # ⚠️ No rollback! Transaction remains in ABORTED state
```

### Impact

- Enrichment fails completely after first database error
- All subsequent database operations fail until connection is closed
- Requires manual intervention (restart process) to recover

### Workaround

1. Restart the enrichment process to get a fresh database connection
2. Terminate stuck connections manually:
   ```bash
   docker exec git-reading-postgres psql -U git_reading_user -d git_reading \
     -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'git_reading' AND pid <> pg_backend_pid();"
   ```

### Solution Implemented

Added transaction rollback in the exception handlers of `execute()` method in `src/load/db/postgres_adapter.py`:

```python
except psycopg.errors.IntegrityError as e:
    self._conn.rollback()  # ← Added
    raise DBIntegrityError(f"Integrity constraint violation: {e}") from e
except psycopg.Error as e:
    self._conn.rollback()  # ← Added
    raise DatabaseError(f"Query execution failed: {e}") from e
```

### Results

- Enrichment now continues smoothly after database errors
- No more "aborted transaction" state issues
- Successfully tested with 476/508 authors enriched

### Related Files

- `src/load/db/postgres_adapter.py` - PostgreSQL adapter implementation
- `src/load/db/interface.py` - DatabaseAdapter interface

---

## Wikidata Performance Issues (RESOLVED)

**Status**: Fixed
**Date Fixed**: 2025-12-29

### Original Problem

- SPARQL queries frequently timed out (60-80% failure rate)
- Retry logic consumed rate limit budget
- 429 "Too Many Requests" errors (10-15 per 120 authors)

### Solution

1. **Flipped search strategy** (`src/enrich/clients/wikidata.py` line 204-225)
   - Primary: Search API (faster, more reliable)
   - Fallback: SPARQL (for edge cases)

2. **Extracted configuration constants** (line 36-42)
   - `MAX_RETRIES = 3`
   - `RETRY_BASE_DELAY = 2`
   - `SPARQL_TIMEOUT = 60`
   - `SEARCH_API_TIMEOUT = 30`
   - `ENTITY_FETCH_TIMEOUT = 30`
   - `SEARCH_RESULT_LIMIT = 10`

3. **Reduced rate limit** (`src/enrich/orchestrator.py` line 40)
   - Changed from 60 to 30 requests/minute

### Results

- **93.7% enrichment success rate** (476/508 authors)
- **490 author influence relationships** captured
- Significantly fewer timeouts (Search API rarely fails)
- Cleaner logs (SPARQL only used when Search API fails)
- Better rate limit compliance
- No 429 rate limit errors during full enrichment run
