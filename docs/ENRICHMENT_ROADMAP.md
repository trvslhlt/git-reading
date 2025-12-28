# Data Enrichment Roadmap

This document outlines the phased approach to enriching book metadata in the git-reading system.

---

## Phase 1: Basic Enrichment ✅ COMPLETED

**Goal**: Enrich books with basic metadata from Open Library

**Implementation**: Completed in earlier sessions

**Coverage Achieved**:
- **Subjects**: ~70% of books
- **Publication Year**: ~84% of books
- **ISBN-13**: ~42% of books (after bug fix)
- **ISBN-10**: ~40-60% of books

**Key Components**:
- ✅ Open Library API client ([src/enrich/clients/openlibrary.py](../src/enrich/clients/openlibrary.py))
- ✅ Book metadata normalizer ([src/enrich/normalizers/book_normalizer.py](../src/enrich/normalizers/book_normalizer.py))
- ✅ Enrichment CLI ([src/enrich/cli.py](../src/enrich/cli.py))
- ✅ Database schema for enrichment data
- ✅ Source tracking system
- ✅ Incremental enrichment support

**Bugs Fixed**:
- ✅ ISBN fetching bug (using `cover_edition_key` instead of `edition_key`)
- ✅ Orphaned records cleanup in incremental load

---

## Phase 2: Cross-Reference Enrichment (IN PROGRESS)

**Goal**: Link books across multiple knowledge bases for richer metadata

### 2.1 Wikidata Integration ✅ BASIC IMPLEMENTATION COMPLETE

**Why**: Wikidata provides structured data about books, authors, literary movements, and influences

**Data to Fetch**:
- ✅ Author biographical data (birth/death dates, nationality)
- ✅ Literary movements and genres (Q-IDs captured, label resolution pending)
- ✅ Thematic tags and concepts
- ✅ Awards and recognition
- ⏳ Translations and editions (schema ready, not yet implemented)
- ⏳ Influence relationships (schema ready, not yet implemented)

**Implementation Status**:
1. ✅ Create Wikidata SPARQL API client
2. ✅ ISBN/title+author → Wikidata entity lookup
3. ✅ Fetch structured data about works and authors
4. ✅ Store in database with source tracking (via `wikidata_id` fields)
5. ✅ Create enrichment workflow integrated with existing CLI

**Files Created**:
- [src/enrich/clients/wikidata.py](../src/enrich/clients/wikidata.py) - SPARQL API client
- [src/enrich/normalizers/wikidata_normalizer.py](../src/enrich/normalizers/wikidata_normalizer.py) - Data normalizers
- [tests/enrich/test_wikidata_normalizer.py](../tests/enrich/test_wikidata_normalizer.py) - Unit tests

**Usage**:
```bash
# Enrich books from both Open Library and Wikidata
enrich-db enrich --sources openlibrary wikidata --limit 10

# Enrich only from Wikidata
enrich-db enrich --sources wikidata --limit 10
```

**Limitations & Future Work**:
- Q-IDs are currently stored instead of labels (e.g., "Q84" instead of "London")
- Need to implement Q-ID → label resolution for subjects, places, movements
- Author influence graph not yet populated (method exists in client)
- Literary movements captured but not stored in `literary_movements` table
- ISBN search in Wikidata has low coverage (prefer title+author search)

**Database Impact**:
- ✅ Uses existing `wikidata_id` fields in `books` and `authors` tables
- ✅ `book_subjects` with source='wikidata'
- ⏳ `author_influences` table (exists but not populated)
- ⏳ `literary_movements` table (exists but not populated)
- ⏳ Awards table (data captured but not stored)

### 2.2 WorldCat/Library of Congress

**Why**: Authoritative library data, especially for older works

**Data to Fetch**:
- Authoritative author names (standardization)
- Dewey/LC classifications
- Physical descriptions
- Alternative titles

### 2.3 Google Books API

**Why**: Book previews, full-text search, popular passages

**Data to Fetch**:
- Book descriptions (often more detailed than Open Library)
- Preview availability
- Popular passages/quotes
- Related books

---

## Phase 3: Derived Data & Analytics (FUTURE)

**Goal**: Generate insights from enriched data

### 3.1 Author Networks

- Build graph of author influences
- Identify literary clusters
- Temporal analysis of reading patterns

### 3.2 Thematic Analysis

- Topic modeling across notes
- Theme extraction from book subjects
- Reading pattern analysis

### 3.3 Reading Statistics

- Books per author/movement/subject
- Reading velocity over time
- Genre distribution
- Temporal trends in interests

---

## Phase 4: Enhanced Search (FUTURE)

**Goal**: Use enriched metadata to improve search capabilities

### 4.1 Metadata-Enhanced Search

- Search by literary movement
- Find books by author influences
- Filter by publication era
- Subject-based recommendations

### 4.2 Graph-Based Discovery

- "Books similar to X" based on metadata
- "Authors influenced by Y"
- "Books in the same movement"

---

## Technical Debt & Improvements

### Priority: High

1. **Incremental Enrichment Optimization**
   - Batch API requests to reduce latency
   - Implement rate limiting and retry logic
   - Cache API responses

2. **Data Quality**
   - Confidence scores for enriched data
   - Conflict resolution when sources disagree
   - Data validation and cleanup

### Priority: Medium

3. **Monitoring & Observability**
   - Track enrichment success rates
   - Alert on API failures
   - Dashboard for enrichment coverage

4. **Testing**
   - Integration tests for API clients
   - Mock API responses for unit tests
   - Test coverage for edge cases

### Priority: Low

5. **Performance**
   - Parallel enrichment of multiple books
   - Async API calls
   - Database query optimization

---

## Decision Points

### Should We Proceed with Phase 2?

**Questions to consider**:
1. Is current enrichment coverage sufficient for your use case?
2. Do you need biographical data about authors?
3. Would cross-referencing with Wikidata add value?
4. Are there specific metadata gaps you want to fill?

**Estimated Effort**:
- Phase 2.1 (Wikidata): ~3-5 days
- Phase 2.2 (WorldCat): ~2-3 days
- Phase 2.3 (Google Books): ~2-3 days

### Alternative Priorities

Instead of Phase 2 enrichment, you might prioritize:
- **Analytics Dashboard**: Visualize current enriched data
- **Advanced Search**: Use existing metadata for better discovery
- **Export Features**: Generate reading lists, citations, etc.
- **Integration**: Connect to other tools (Goodreads, LibraryThing)

---

## Next Steps

**To continue with Phase 2**:
1. Choose which data source to integrate first (recommend Wikidata)
2. Review database schema additions
3. Design API client and normalization strategy
4. Implement incremental enrichment workflow
5. Test on subset of books
6. Roll out to full database

**To explore alternatives**:
1. Review current enrichment coverage with `make run-enrich-status`
2. Identify specific metadata needs
3. Prioritize based on value vs. effort
4. Create focused implementation plan

---

## References

- [Wikidata SPARQL](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service)
- [Google Books API](https://developers.google.com/books)
- [WorldCat Search API](https://www.oclc.org/developer/develop/web-services/worldcat-search-api.en.html)
- [Open Library API Docs](https://openlibrary.org/developers/api)
