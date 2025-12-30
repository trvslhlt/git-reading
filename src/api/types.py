"""GraphQL type definitions for the git-reading API."""

import strawberry


@strawberry.type
class NodeMetadata:
    """Metadata for graph nodes used in visualization."""

    birth_year: int | None = None
    death_year: int | None = None
    publication_year: int | None = None


@strawberry.type
class Author:
    """Author entity with biographical information."""

    id: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    birth_place: str | None = None
    nationality: str | None = None
    bio: str | None = None
    wikidata_id: str | None = None
    viaf_id: str | None = None


@strawberry.type
class Book:
    """Book entity with publication information."""

    id: str
    title: str
    publication_year: int | None = None
    date_read: str | None = None
    isbn_13: str | None = None
    isbn_10: str | None = None
    openlibrary_id: str | None = None
    wikidata_id: str | None = None


@strawberry.type
class GraphNode:
    """Node in the graph visualization."""

    id: str
    type: str  # "author" or "book"
    label: str
    metadata: NodeMetadata


@strawberry.type
class GraphEdge:
    """Edge connecting two nodes in the graph."""

    source: str
    target: str
    type: str  # "authored", "influenced"


@strawberry.type
class Graph:
    """Complete graph structure with nodes and edges."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
