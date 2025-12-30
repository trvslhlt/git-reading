# GraphQL API Usage Guide

Complete guide to using the git-reading GraphQL API with example requests and responses.

## Table of Contents

- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Query Examples](#query-examples)
  - [Search for Authors](#search-for-authors)
  - [Get Author Details](#get-author-details)
  - [Get Book Details](#get-book-details)
  - [Get Author Graph](#get-author-graph)
- [Advanced Usage](#advanced-usage)
- [GraphQL Playground](#graphql-playground)
- [Using with curl](#using-with-curl)
- [Integration Examples](#integration-examples)

---

## Quick Start

### Start the API Server

```bash
# One-command setup and launch (auto-opens GraphQL Playground)
make api

# Or manually
make api-install
make run-api  # Also auto-opens browser
```

The server will be available at:
- **GraphQL Playground**: http://localhost:8000/graphql (opens automatically in browser)
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

### Verify Server is Running

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy"
}
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/graphql` | GraphQL endpoint (POST) |
| `/` | API information |
| `/health` | Health check |
| `/docs` | Interactive API documentation (Swagger UI) |

---

## Query Examples

### Search for Authors

Search for authors by name using partial matching (case-insensitive).

**GraphQL Query:**
```graphql
query SearchAuthors {
  searchAuthors(query: "king", limit: 3) {
    id
    name
    birthYear
    deathYear
    nationality
    wikidataId
  }
}
```

**curl Command:**
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ searchAuthors(query: \"king\", limit: 3) { id name birthYear deathYear } }"
  }'
```

**Response:**
```json
{
  "data": {
    "searchAuthors": [
      {
        "id": "stephen-king",
        "name": "Stephen King",
        "birthYear": null,
        "deathYear": null,
        "nationality": null,
        "wikidataId": null
      }
    ]
  }
}
```

**Parameters:**
- `query` (required): Search term for author name
- `limit` (optional, default: 10): Maximum number of results

**Use Cases:**
- Autocomplete for author search
- Finding authors by partial name
- Building search interfaces

---

### Get Author Details

Fetch complete information about a specific author.

**GraphQL Query:**
```graphql
query GetAuthor {
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

**curl Command:**
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ author(id: \"stephen-king\") { id name birthYear deathYear nationality bio } }"
  }'
```

**Response:**
```json
{
  "data": {
    "author": {
      "id": "stephen-king",
      "name": "Stephen King",
      "firstName": null,
      "lastName": null,
      "birthYear": null,
      "deathYear": null,
      "birthPlace": null,
      "nationality": null,
      "bio": null,
      "wikidataId": null,
      "viafId": null
    }
  }
}
```

**Parameters:**
- `id` (required): Author ID (slug format: lowercase-with-hyphens)

**Notes:**
- Returns `null` if author not found
- Enrichment data (birthYear, nationality, etc.) requires running `make run-enrich`

---

### Get Book Details

Fetch complete information about a specific book.

**GraphQL Query:**
```graphql
query GetBook {
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

**curl Command:**
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ book(id: \"the-stand_stephen-king\") { id title publicationYear isbn13 openlibraryId } }"
  }'
```

**Response:**
```json
{
  "data": {
    "book": {
      "id": "the-stand_stephen-king",
      "title": "The Stand",
      "publicationYear": 1978,
      "dateRead": null,
      "isbn13": null,
      "isbn10": null,
      "openlibraryId": "OL81618W",
      "wikidataId": null
    }
  }
}
```

**Parameters:**
- `id` (required): Book ID (format: title_author)

**Book ID Format:**
Book IDs are generated from the title and primary author:
- Title: "The Stand"
- Author: "Stephen King"
- ID: `the-stand_stephen-king`

---

### Get Author Graph

Retrieve a graph structure centered on an author, including their books and influence relationships.

#### Books Only (depth=0)

**GraphQL Query:**
```graphql
query AuthorBooksGraph {
  authorGraph(authorId: "stephen-king", depth: 0) {
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

**Response:**
```json
{
  "data": {
    "authorGraph": {
      "nodes": [
        {
          "id": "stephen-king",
          "type": "author",
          "label": "Stephen King",
          "metadata": {
            "birthYear": null,
            "deathYear": null,
            "publicationYear": null
          }
        },
        {
          "id": "the-stand_stephen-king",
          "type": "book",
          "label": "The Stand",
          "metadata": {
            "birthYear": null,
            "deathYear": null,
            "publicationYear": 1978
          }
        }
      ],
      "edges": [
        {
          "source": "stephen-king",
          "target": "the-stand_stephen-king",
          "type": "authored"
        }
      ]
    }
  }
}
```

#### With Influence Relationships (depth=1)

**GraphQL Query:**
```graphql
query AuthorInfluenceGraph {
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

**curl Command:**
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ authorGraph(authorId: \"stephen-king\", depth: 1) { nodes { id type label } edges { source target type } } }"
  }'
```

**Response:**
```json
{
  "data": {
    "authorGraph": {
      "nodes": [
        {
          "id": "stephen-king",
          "type": "author",
          "label": "Stephen King",
          "metadata": {
            "birthYear": null,
            "publicationYear": null
          }
        },
        {
          "id": "the-stand_stephen-king",
          "type": "book",
          "label": "The Stand",
          "metadata": {
            "birthYear": null,
            "publicationYear": 1978
          }
        },
        {
          "id": "joseph-strickland",
          "type": "author",
          "label": "Joseph Strickland",
          "metadata": {
            "birthYear": null,
            "publicationYear": null
          }
        },
        {
          "id": "clive-barker",
          "type": "author",
          "label": "Clive Barker",
          "metadata": {
            "birthYear": null,
            "publicationYear": null
          }
        }
      ],
      "edges": [
        {
          "source": "stephen-king",
          "target": "the-stand_stephen-king",
          "type": "authored"
        },
        {
          "source": "stephen-king",
          "target": "joseph-strickland",
          "type": "influenced"
        },
        {
          "source": "stephen-king",
          "target": "clive-barker",
          "type": "influenced"
        }
      ]
    }
  }
}
```

**Parameters:**
- `authorId` (required): ID of the center author
- `depth` (optional, default: 1):
  - `0` = Author and their books only
  - `1` = Include author influence relationships (who they influenced and who influenced them)

**Graph Structure:**
- **Nodes**: Each node represents an author or book
  - `id`: Unique identifier
  - `type`: Either `"author"` or `"book"`
  - `label`: Display name
  - `metadata`: Additional data for visualization
- **Edges**: Each edge represents a relationship
  - `source`: Starting node ID
  - `target`: Ending node ID
  - `type`: Either `"authored"` (author → book) or `"influenced"` (author → author)

**Use Cases:**
- Building interactive graph visualizations
- Exploring author influence networks
- Finding connections between authors
- Displaying author bibliographies

---

## Advanced Usage

### Combined Query (Multiple Operations)

You can request multiple pieces of data in a single query:

**GraphQL Query:**
```graphql
query ExploreAuthor {
  # Search for authors
  searchResults: searchAuthors(query: "king", limit: 3) {
    id
    name
  }

  # Get specific author details
  authorDetails: author(id: "stephen-king") {
    id
    name
    birthYear
    nationality
  }

  # Get their graph
  authorGraph: authorGraph(authorId: "stephen-king", depth: 1) {
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

**Response:**
```json
{
  "data": {
    "searchResults": [
      {
        "id": "stephen-king",
        "name": "Stephen King"
      }
    ],
    "authorDetails": {
      "id": "stephen-king",
      "name": "Stephen King",
      "birthYear": null,
      "nationality": null
    },
    "authorGraph": {
      "nodes": [...],
      "edges": [...]
    }
  }
}
```

### Using Variables

For dynamic queries, use GraphQL variables:

**GraphQL Query:**
```graphql
query GetAuthorGraph($authorId: ID!, $depth: Int!) {
  authorGraph(authorId: $authorId, depth: $depth) {
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

**Variables:**
```json
{
  "authorId": "stephen-king",
  "depth": 1
}
```

**curl Command:**
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetAuthorGraph($authorId: ID!, $depth: Int!) { authorGraph(authorId: $authorId, depth: $depth) { nodes { id type label } edges { source target type } } }",
    "variables": {
      "authorId": "stephen-king",
      "depth": 1
    }
  }'
```

---

## GraphQL Playground

The GraphQL Playground at http://localhost:8000/graphql provides an interactive interface with:

- **Schema Explorer**: Browse all available types and queries
- **Auto-completion**: IntelliSense for GraphQL queries
- **Documentation**: Inline docs for all fields
- **Query History**: Access previous queries
- **Variables Editor**: Test queries with different variables

### Example Workflow in Playground:

1. **Open Playground**: http://localhost:8000/graphql
2. **Type a query**:
   ```graphql
   {
     searchAuthors(query: "king") {
       id
       name
     }
   }
   ```
3. **Click "Play" button** (or Ctrl+Enter)
4. **View results** in right panel
5. **Explore schema** using "Docs" tab on the right

---

## Using with curl

All examples can be executed via curl for automation or testing.

### Basic Template

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "YOUR_GRAPHQL_QUERY_HERE"
  }'
```

### With Pretty Output (using jq)

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ searchAuthors(query: \"king\") { id name } }"
  }' | jq '.'
```

### With Variables

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query($id: ID!) { author(id: $id) { name birthYear } }",
    "variables": {
      "id": "stephen-king"
    }
  }' | jq '.'
```

---

## Integration Examples

### Python with requests

```python
import requests

API_URL = "http://localhost:8000/graphql"

def search_authors(query: str, limit: int = 10):
    """Search for authors by name."""
    graphql_query = """
    query SearchAuthors($query: String!, $limit: Int!) {
      searchAuthors(query: $query, limit: $limit) {
        id
        name
        birthYear
        deathYear
      }
    }
    """

    response = requests.post(
        API_URL,
        json={
            "query": graphql_query,
            "variables": {
                "query": query,
                "limit": limit
            }
        }
    )

    return response.json()

# Usage
results = search_authors("king", limit=5)
authors = results["data"]["searchAuthors"]

for author in authors:
    print(f"{author['name']} ({author['id']})")
```

### JavaScript with fetch

```javascript
const API_URL = "http://localhost:8000/graphql";

async function getAuthorGraph(authorId, depth = 1) {
  const query = `
    query GetAuthorGraph($authorId: ID!, $depth: Int!) {
      authorGraph(authorId: $authorId, depth: $depth) {
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
  `;

  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      variables: {
        authorId,
        depth,
      },
    }),
  });

  const data = await response.json();
  return data.data.authorGraph;
}

// Usage
const graph = await getAuthorGraph("stephen-king", 1);
console.log(`Graph has ${graph.nodes.length} nodes and ${graph.edges.length} edges`);
```

### React with Apollo Client

```jsx
import { ApolloClient, InMemoryCache, gql, useQuery } from '@apollo/client';

const client = new ApolloClient({
  uri: 'http://localhost:8000/graphql',
  cache: new InMemoryCache(),
});

const GET_AUTHOR_GRAPH = gql`
  query GetAuthorGraph($authorId: ID!, $depth: Int!) {
    authorGraph(authorId: $authorId, depth: $depth) {
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
`;

function AuthorGraph({ authorId }) {
  const { loading, error, data } = useQuery(GET_AUTHOR_GRAPH, {
    variables: { authorId, depth: 1 },
  });

  if (loading) return <p>Loading...</p>;
  if (error) return <p>Error: {error.message}</p>;

  const { nodes, edges } = data.authorGraph;

  return (
    <div>
      <h2>Graph for {authorId}</h2>
      <p>{nodes.length} nodes, {edges.length} edges</p>
      {/* Render your graph visualization here */}
    </div>
  );
}
```

---

## Error Handling

### GraphQL Errors

When a query fails, the response includes an `errors` array:

**Request:**
```graphql
{
  author(id: "non-existent-author") {
    name
  }
}
```

**Response:**
```json
{
  "data": {
    "author": null
  }
}
```

**Note**: Null responses are valid for optional fields. Check `data.author` for `null` to handle missing authors.

### HTTP Errors

Non-200 status codes indicate server errors:

```bash
curl -I http://localhost:8000/graphql
# HTTP/1.1 405 Method Not Allowed  (if using GET instead of POST)
```

---

## Best Practices

1. **Use Variables**: For dynamic queries, use variables instead of string interpolation
2. **Request Only What You Need**: GraphQL allows you to specify exactly which fields to return
3. **Handle Null Values**: Many fields are optional and may return `null`
4. **Batch Queries**: Combine multiple queries in one request to reduce round trips
5. **Error Handling**: Always check for both `errors` array and `null` data
6. **Connection Pooling**: The API uses PostgreSQL connection pooling; avoid excessive concurrent requests

---

## Troubleshooting

### API Not Starting

```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill existing process if needed
kill -9 <PID>

# Restart API
make run-api
```

### Database Connection Errors

```bash
# Verify PostgreSQL is running
make postgres-status

# Start PostgreSQL if needed
make postgres-up

# Check database has data
make postgres-psql
# Then run: SELECT COUNT(*) FROM authors;
```

### Empty Results

If queries return empty data:

1. **Check database has data**:
   ```bash
   make postgres-psql
   # SELECT COUNT(*) FROM authors;
   # SELECT COUNT(*) FROM books;
   ```

2. **Run extraction and loading**:
   ```bash
   make run-extract ARGS='--notes-dir /path/to/notes'
   make run-load ARGS='--index-dir data/index'
   ```

3. **Run enrichment** (for influence data):
   ```bash
   make run-enrich ARGS='--sources wikidata --entity-type authors'
   ```

---

## Related Documentation

- [API README](../src/api/README.md) - API implementation details
- [Enrichment Guide](ENRICHMENT_GUIDE.md) - How to populate metadata
- [Database Documentation](DATABASE.md) - Database schema and setup
- [Project Phases](work/PROJECT_PHASES.md) - Overall project roadmap

---

## Next Steps

- **Build a Frontend**: Use the API with Next.js, React Flow for graph visualization
- **Explore the Schema**: Use GraphQL Playground to discover all available queries
- **Enrich Your Data**: Run enrichment to populate author influence relationships
- **Extend the API**: Add custom queries for your specific needs
