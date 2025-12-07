# Vector Search Filtering: Pre vs Post

This document explains the difference between pre-filtering and post-filtering in vector search, and when to use each approach.

## Current Implementation (Post-filtering)

**File:** [src/query/vector_store.py](../src/query/vector_store.py)

### How it works:

```python
# 1. Search ALL vectors
results = store.search(query_embedding, k=50)  # Search 4,174 vectors

# 2. Filter results AFTER search
filtered = []
for chunk, score in results:
    if chunk.author == "John Barth":
        filtered.append((chunk, score))

return filtered[:5]  # Return top 5
```

### Performance:

```
Query: "narrative structure" --author "John Barth"

Vectors searched: 4,174 (100%)
John Barth chunks: ~50 (1.2%)
Wasted computation: 98.8%
```

**When to use:**
- No filters or very broad filters
- Small datasets (<10k vectors)
- Filters that match >50% of vectors

---

## Enhanced Implementation (Pre-filtering)

**File:** [src/query/vector_store_filtered.py](../src/query/vector_store_filtered.py)

### How it works:

```python
# 1. Look up which vectors match filter (fast - just hash table lookup)
john_barth_indices = author_to_indices["John Barth"]  # [42, 137, 201, ...]

# 2. Extract ONLY those vectors
filtered_vectors = [index.reconstruct(i) for i in john_barth_indices]

# 3. Create temporary index with just those vectors
temp_index = faiss.IndexFlatL2(dimension)
temp_index.add(filtered_vectors)

# 4. Search ONLY the filtered vectors
results = temp_index.search(query_embedding, k=5)  # Search ~50 vectors

# 5. Map back to original chunks
return [chunks[original_idx] for original_idx in results]
```

### Performance:

```
Query: "narrative structure" --author "John Barth"

Vectors searched: ~50 (1.2%)
John Barth chunks: ~50 (1.2%)
Wasted computation: 0%
Speedup: ~83x
```

**When to use:**
- Selective filters (<10% of data)
- Large datasets (>100k vectors)
- Multiple filters combined

---

## Performance Comparison

### Your Dataset (4,174 vectors)

| Filter | Chunks Matched | Post-filter | Pre-filter | Speedup |
|--------|---------------|-------------|------------|---------|
| None | 4,174 (100%) | 4,174 | 4,174 | 1x |
| author="John Barth" | ~50 (1.2%) | 4,174 | 50 | **83x** |
| section="excerpts" | ~1,800 (43%) | 4,174 | 1,800 | **2.3x** |
| author="John Barth" AND section="notes" | ~30 (0.7%) | 4,174 | 30 | **139x** |

### Larger Dataset (100k vectors)

| Filter | Chunks Matched | Post-filter | Pre-filter | Speedup |
|--------|---------------|-------------|------------|---------|
| author="John Barth" | ~1,200 (1.2%) | 100,000 | 1,200 | **83x** |
| Multiple filters | ~100 (0.1%) | 100,000 | 100 | **1000x** |

---

## Implementation Details

### Lookup Table Structure

```python
# Built during indexing
author_to_indices = {
    "John Barth": [5, 42, 137, 201, 389, ...],  # List of vector indices
    "Jorge Luis Borges": [12, 88, 156, ...],
    "Aristotle": [3, 99, 234, ...],
}

section_to_indices = {
    "notes": [0, 2, 5, 8, 11, ...],
    "excerpts": [1, 3, 6, 9, 12, ...],
}
```

**Memory overhead:** ~50 bytes per chunk = ~200 KB for 4,174 chunks

### Filter Combination

Filters use set intersection for AND logic:

```python
# author="John Barth" AND section="notes"
author_set = {5, 42, 137, 201, 389, ...}
section_set = {0, 2, 5, 8, 11, ...}
valid_indices = author_set & section_set  # {5, 11, 42, ...}
```

Very fast: O(min(len(author_set), len(section_set)))

---

## Trade-offs

### Post-filtering (Current)

**Pros:**
- Simpler implementation
- No additional memory
- No index building overhead
- Good for broad filters

**Cons:**
- Wastes computation on filtered-out vectors
- Slower for selective filters
- Gets much slower as dataset grows

### Pre-filtering (Enhanced)

**Pros:**
- Much faster for selective filters
- Scales better with dataset size
- No wasted computation
- Can combine multiple filters efficiently

**Cons:**
- Slight memory overhead for lookup tables (~5%)
- Reconstructing vectors has some overhead
- More complex implementation
- Overkill for very small datasets

---

## When to Switch

**Stick with post-filtering if:**
- Dataset < 10,000 vectors
- Filters match > 50% of data
- You rarely use filters

**Switch to pre-filtering if:**
- Dataset > 50,000 vectors
- Filters are selective (< 10% of data)
- You frequently filter by author/section
- You combine multiple filters

**For your current dataset (4,174 vectors):**
- Post-filtering is fine for most queries
- Pre-filtering worth it for author-specific queries
- Consider pre-filtering if dataset will grow >10k

---

## Future Optimizations

### 1. Persistent Filtered Indexes

Instead of rebuilding temp index every query:

```python
# Build once, save to disk
for author in unique_authors:
    author_index = build_index_for_author(author)
    save(f".tmp/vector_store/by_author/{author}/")
```

**Trade-off:** Disk space vs query speed

### 2. FAISS IVF Index

For very large datasets (>1M vectors):

```python
# Inverted file index with clustering
index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters=100)
```

**Benefit:** Sub-linear search time
**Cost:** More complex, approximate results

### 3. Hybrid Approach

Use pre-filtering when selectivity < threshold:

```python
if len(valid_indices) < 0.1 * total_vectors:
    return pre_filter_search(...)
else:
    return post_filter_search(...)
```

**Benefit:** Best of both worlds

---

## Example Usage

### Using the Filtered Store

```python
from query.vector_store_filtered import FilteredVectorStore
from query.embeddings import EmbeddingModel

# Build with filtering support
store = FilteredVectorStore(dimension=384)
store.add(embeddings, chunks)
store.save(".tmp/vector_store_filtered/")

# Search with pre-filtering
model = EmbeddingModel()
query_emb = model.encode_single("narrative structure")

results = store.search(
    query_emb,
    k=5,
    filter_author="John Barth",  # Pre-filtered!
    filter_section="notes"       # Combined with AND
)

# Check filter info before searching
info = store.get_filter_info(author="John Barth", section="notes")
print(f"Will search {info['filtered_chunks']} vectors")
print(f"Reduction: {info['reduction_percent']:.1f}%")
```

---

## Benchmarks

Run your own benchmarks:

```bash
# Time post-filtering
time make run-search-query ARGS='"narrative" --author "John Barth"'

# Time pre-filtering (after switching to FilteredVectorStore)
time make run-search-query ARGS='"narrative" --author "John Barth"'
```

For your dataset, you should see:
- Unfiltered: ~200-300ms
- Post-filtered (author): ~200-300ms (same, filters afterward)
- Pre-filtered (author): ~20-50ms (10x faster)

---

## Recommendation for Your Project

**Short term:** Keep post-filtering
- Your dataset is small (4,174 vectors)
- Current performance is good (~200-500ms)
- Simpler to maintain

**Long term:** Consider pre-filtering when:
- Dataset grows > 10,000 vectors
- You add more metadata fields to filter
- You want to support complex queries (author AND section AND date range)

**Best of both:** Implement hybrid approach that auto-selects based on filter selectivity.
