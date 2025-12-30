# Wikidata Integration (Phase 2.1)

This document describes the Wikidata integration for enriching book and author metadata.

## Overview

The Wikidata integration adds a second data source for enriching book and author metadata beyond Open Library. Wikidata is a free knowledge base that can be read and edited by humans and machines, containing structured data about millions of books, authors, and literary works.

## What Was Implemented

### Core Components

1. **WikidataClient** ([src/enrich/clients/wikidata.py](../src/enrich/clients/wikidata.py))
   - SPARQL query endpoint integration
   - Book search by ISBN, title+author
   - Author search by name
   - Entity data fetching
   - Literary movement extraction
   - Author influence graph queries (implemented but not yet integrated)

2. **Normalizers** ([src/enrich/normalizers/wikidata_normalizer.py](../src/enrich/normalizers/wikidata_normalizer.py))
   - `WikidataBookNormalizer` - Converts Wikidata book entities to our schema
   - `WikidataAuthorNormalizer` - Converts Wikidata author entities to our schema

3. **Orchestrator Updates** ([src/enrich/orchestrator.py](../src/enrich/orchestrator.py))
   - Multi-source enrichment support
   - Fallback strategy: ISBN search → title+author search
   - Source tracking in enrichment logs

4. **Tests** ([tests/enrich/test_wikidata_normalizer.py](../tests/enrich/test_wikidata_normalizer.py))
   - 8 unit tests covering normalizer functionality
   - Tests for both book and author normalization
   - Edge case handling (missing fields, wrong source)

## Usage

### Basic Enrichment

```bash
# Enrich from both Open Library and Wikidata
enrich-db enrich --sources openlibrary wikidata --limit 10

# Enrich only from Wikidata
enrich-db enrich --sources wikidata

# Enrich with default source (Open Library only)
enrich-db enrich
```

### Data Captured

**For Books**:
- Wikidata ID (`wikidata_id`)
- ISBN-10 and ISBN-13
- Publication year
- Language
- Description
- Subjects/genres (as Q-IDs)
- Literary movements (as Q-IDs)
- Awards (captured but not stored yet)

**For Authors** (schema ready, enrichment not yet implemented):
- Wikidata ID
- Birth/death years
- Birth/death places (as Q-IDs)
- Nationality (as Q-ID)
- Biography
- Wikipedia URL
- VIAF ID
- Literary movements

## Current Limitations

### 1. Q-ID vs. Label Storage

Currently, many fields store Wikidata Q-IDs instead of human-readable labels:

```python
# Current implementation
"birth_place": "Q84"  # Should be "London"
"nationality": "Q145"  # Should be "United Kingdom"
"subjects": ["Q24925"]  # Should be ["Science fiction"]
```

**Future Work**: Implement Q-ID → label resolution via additional SPARQL queries or entity fetching.

### 2. Limited ISBN Coverage

ISBN search in Wikidata has relatively low coverage compared to title+author search. The client implements a fallback strategy:

1. Try ISBN search if ISBN available
2. Fall back to title+author search
3. Return None if both fail

### 3. Features Not Yet Integrated

The following features are implemented in the client but not yet integrated into the enrichment workflow:

- **Author influence relationships** - `get_author_influences()` method exists
- **Literary movements** - Data captured but not stored in `literary_movements` table
- **Awards** - Data captured but no database table yet
- **Author enrichment** - Only book enrichment currently supported

### 4. SPARQL Query Performance

Some SPARQL queries can be slow (>30 seconds), particularly:
- Author searches with complex filters
- Queries with multiple OPTIONAL clauses

Consider implementing query timeouts and retry logic for production use.

## Database Schema

The schema was already prepared for Wikidata integration in Phase 1:

**Existing fields used**:
- `books.wikidata_id` - Wikidata Q-number for books
- `authors.wikidata_id` - Wikidata Q-number for authors
- `authors.wikipedia_url` - Wikipedia link
- `authors.viaf_id` - VIAF identifier
- `book_subjects` with `source='wikidata'`

**Tables ready but not populated**:
- `literary_movements` - Literary movement taxonomy
- `author_movements` - Author → movement relationships
- `author_influences` - Author influence graph

**Tables needed for future work**:
- `book_awards` - Award information
- `author_biographical_data` - Extended biographical details

## Testing

### Unit Tests

```bash
PYTHONPATH=src uv run pytest tests/enrich/test_wikidata_normalizer.py -v
```

All 8 tests should pass, covering:
- Basic field normalization
- Subject extraction
- Missing field handling
- Error handling for wrong source

### Integration Testing

Create a test script to verify live API access:

```python
from enrich.clients.wikidata import WikidataClient
from enrich.normalizers.wikidata_normalizer import WikidataBookNormalizer

client = WikidataClient()
normalizer = WikidataBookNormalizer()

# Search for a well-known book
result = client.search_book("Neuromancer", "William Gibson")
if result:
    normalized = normalizer.normalize(result, "wikidata")
    print(f"Found: {normalized['wikidata_id']}")
    print(f"Published: {normalized['publication_year']}")

client.close()
```

## Next Steps (Phase 2.2)

1. **Q-ID Label Resolution**
   - Implement label fetching for Q-IDs
   - Cache label mappings to reduce API calls
   - Update normalizers to return labels instead of IDs

2. **Author Enrichment Workflow**
   - Extend orchestrator to support author enrichment
   - Populate `authors` table biographical fields
   - Implement author influence graph population

3. **Literary Movements Integration**
   - Store movements in `literary_movements` table
   - Link authors to movements via `author_movements`
   - Enable movement-based search and filtering

4. **Awards Table**
   - Create `book_awards` table
   - Store award data with year and category
   - Link to books

5. **Performance Optimization**
   - Implement query result caching
   - Batch entity lookups
   - Add retry logic with exponential backoff

## API Rate Limits

- **Current limit**: 60 requests per minute (conservative)
- **Wikidata's official limit**: No strict limit, but be respectful
- **Recommendation**: Keep at 60 req/min to avoid potential blocking

## Resources

- [Wikidata SPARQL Query Service](https://query.wikidata.org/)
- [Wikidata API Documentation](https://www.wikidata.org/wiki/Wikidata:Data_access)
- [SPARQL Tutorial](https://www.wikidata.org/wiki/Wikidata:SPARQL_tutorial)
- [Wikidata Property List](https://www.wikidata.org/wiki/Wikidata:List_of_properties)

## Example SPARQL Queries

### Find Book by Title and Author

```sparql
SELECT ?book ?bookLabel WHERE {
  ?book wdt:P31 wd:Q7725634 .  # instance of: literary work
  ?book rdfs:label ?title .
  ?book wdt:P50 ?author .
  ?author rdfs:label ?authorName .

  FILTER(CONTAINS(LCASE(?title), "neuromancer"))
  FILTER(CONTAINS(LCASE(?authorName), "gibson"))
  FILTER(LANG(?title) = "en")

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 1
```

### Get Literary Movements for Author

```sparql
SELECT DISTINCT ?movement ?movementLabel WHERE {
  wd:Q561571 wdt:P135 ?movement .  # Q561571 = William Gibson
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

### Get Author Influences

```sparql
SELECT ?influencer ?influencerLabel ?influenced ?influencedLabel WHERE {
  {
    wd:Q561571 wdt:P737 ?influencer .  # influenced by
    BIND(wd:Q561571 AS ?influenced)
  } UNION {
    ?influenced wdt:P737 wd:Q561571 .  # this author influenced others
    BIND(wd:Q561571 AS ?influencer)
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```
