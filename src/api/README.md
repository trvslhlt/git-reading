# Git-Reading GraphQL API

GraphQL API for exploring reading data through interactive graphs.

## Features

- **Author-Book Graph Visualization**: Query author networks with their books and influence relationships
- **Author Search**: Search for authors by name
- **Flexible Queries**: Fetch individual authors or books with all their metadata

## Quick Start

### Installation

Install the API dependencies:

```bash
uv pip install -e ".[api]"
```

### Running the Server

Start the API server:

```bash
PYTHONPATH=src uv run uvicorn api.main:app --reload --port 8000
```

The server will start at:
- API: http://localhost:8000
- GraphQL Playground: http://localhost:8000/graphql
- Health Check: http://localhost:8000/health
- API Docs: http://localhost:8000/docs

## GraphQL Schema

### Queries

#### `authorGraph`

Get a graph centered on an author with their books and influence relationships.

```graphql
query {
  authorGraph(authorId: "stephen-king", depth: 1) {
    nodes {
      id
      type
      label
      metadata {
        birthYear
        deathYear
        publicationYear
      }
    }
    edges {
      source
      target
      type
    }
  }
}
```

**Parameters:**
- `authorId` (required): ID of the center author
- `depth` (optional, default: 1):
  - `0` = Author and their books only
  - `1+` = Include author influence relationships

**Returns:**
- `nodes`: List of graph nodes (authors and books)
- `edges`: List of graph edges (authored, influenced)

#### `searchAuthors`

Search for authors by name (partial matching).

```graphql
query {
  searchAuthors(query: "king", limit: 5) {
    id
    name
    birthYear
    deathYear
    nationality
    wikidataId
  }
}
```

**Parameters:**
- `query` (required): Search term
- `limit` (optional, default: 10): Maximum results to return

#### `author`

Get a single author by ID.

```graphql
query {
  author(id: "stephen-king") {
    id
    name
    firstName
    lastName
    birthYear
    deathYear
    birthPlace
    nationality
    bio
    wikidataId
    viafId
  }
}
```

#### `book`

Get a single book by ID.

```graphql
query {
  book(id: "the-stand_stephen-king") {
    id
    title
    publicationYear
    dateRead
    isbn13
    isbn10
    openlibraryId
    wikidataId
  }
}
```

## Example Queries

### Find Authors Named "King" and Get Their Graph

```graphql
query {
  authors: searchAuthors(query: "king", limit: 3) {
    id
    name
  }
}
```

Then use the returned ID:

```graphql
query {
  authorGraph(authorId: "stephen-king", depth: 1) {
    nodes {
      id
      type
      label
      metadata {
        birthYear
        publicationYear
      }
    }
    edges {
      source
      target
      type
    }
  }
}
```

### Get Author with Influence Network

```graphql
query {
  authorGraph(authorId: "stephen-king", depth: 1) {
    nodes {
      id
      type
      label
    }
    edges {
      source
      target
      type
    }
  }
}
```

## Data Model

### GraphNode

Represents a node in the graph visualization.

- `id`: Unique identifier
- `type`: Node type (`"author"` or `"book"`)
- `label`: Display name
- `metadata`: Additional data for visualization
  - `birthYear`: Author birth year
  - `deathYear`: Author death year
  - `publicationYear`: Book publication year

### GraphEdge

Represents a connection between nodes.

- `source`: Source node ID
- `target`: Target node ID
- `type`: Edge type
  - `"authored"`: Author wrote book (author → book)
  - `"influenced"`: Author influenced another (influencer → influenced)

## Architecture

The API is built with:

- **FastAPI**: Modern Python web framework
- **Strawberry GraphQL**: GraphQL library for Python
- **Database Adapter Pattern**: Abstracts SQLite/PostgreSQL differences

### File Structure

```
src/api/
├── __init__.py           # Package init
├── main.py              # FastAPI app with GraphQL router
├── schema.py            # GraphQL schema definition
├── types.py             # GraphQL type definitions
├── resolvers/
│   ├── __init__.py
│   └── graph.py         # Query resolvers
└── README.md            # This file
```

## CORS Configuration

The API is configured to allow requests from Next.js development servers:
- http://localhost:3000
- http://localhost:3001

To add more origins, edit [main.py](main.py:14-20):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Development

### Testing with curl

Search for authors:
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ searchAuthors(query: \"king\") { id name } }"}'
```

Get author graph:
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ authorGraph(authorId: \"stephen-king\") { nodes { id label } edges { source target } } }"}'
```

### GraphQL Playground

Visit http://localhost:8000/graphql in your browser for an interactive GraphQL playground where you can:
- Explore the schema
- Build queries with autocomplete
- See query results in real-time

## Next Steps

With the API running, you can now:

1. **Build Frontend**: Create a Next.js app with React Flow for graph visualization
2. **Add Enrichment**: Run enrichment to populate author influence data
3. **Extend Schema**: Add subjects, literary movements, and awards
4. **Add Mutations**: Enable editing relationships via GraphQL

## Related Documentation

- [Project Overview](../../README.md)
- [Enrichment Roadmap](../../docs/ENRICHMENT_ROADMAP.md)
- [Project Phases](../../docs/PROJECT_PHASES.md)
