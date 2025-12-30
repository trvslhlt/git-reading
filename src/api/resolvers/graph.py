"""Graph query resolvers for author and book networks."""

import strawberry

from api.types import Author, Book, Graph, GraphEdge, GraphNode, NodeMetadata
from load.db.factory import get_adapter


@strawberry.type
class Query:
    """GraphQL queries for the git-reading API."""

    @strawberry.field
    def author_graph(self, author_id: str, depth: int = 1) -> Graph:
        """
        Build graph centered on an author.

        Returns a graph with:
        - Author node (center)
        - Book nodes (books by this author)
        - Edges: author -> book (authored)
        - If depth >= 1: Include influenced/influencer authors
        - Edges: author -> author (influenced)

        Args:
            author_id: ID of the center author
            depth: How many levels of influence to include (0 = books only, 1+ = influences)

        Returns:
            Graph with nodes and edges for visualization
        """
        adapter = get_adapter()
        adapter.connect()

        nodes = []
        edges = []
        seen_authors = set()
        seen_books = set()

        try:
            # 1. Center author
            author_row = adapter.fetchone(
                f"SELECT * FROM authors WHERE id = {adapter.placeholder}", (author_id,)
            )

            if not author_row:
                return Graph(nodes=[], edges=[])

            seen_authors.add(author_id)
            nodes.append(
                GraphNode(
                    id=author_row["id"],
                    type="author",
                    label=author_row["name"],
                    metadata=NodeMetadata(
                        birth_year=author_row.get("birth_year"),
                        death_year=author_row.get("death_year"),
                    ),
                )
            )

            # 2. Author's books
            books_query = f"""
                SELECT b.* FROM books b
                JOIN book_authors ba ON b.id = ba.book_id
                WHERE ba.author_id = {adapter.placeholder}
            """
            books = adapter.fetchall(books_query, (author_id,))

            for book in books:
                book_id = book["id"]
                if book_id not in seen_books:
                    seen_books.add(book_id)
                    nodes.append(
                        GraphNode(
                            id=book_id,
                            type="book",
                            label=book["title"],
                            metadata=NodeMetadata(publication_year=book.get("publication_year")),
                        )
                    )
                    edges.append(GraphEdge(source=author_id, target=book_id, type="authored"))

            # 3. If depth >= 1: Include influence relationships
            if depth >= 1:
                # Authors who influenced this one
                influencers_query = f"""
                    SELECT a.* FROM authors a
                    JOIN author_influences ai ON a.id = ai.influencer_id
                    WHERE ai.influenced_id = {adapter.placeholder}
                """
                influencers = adapter.fetchall(influencers_query, (author_id,))

                for influencer in influencers:
                    influencer_id = influencer["id"]
                    if influencer_id not in seen_authors:
                        seen_authors.add(influencer_id)
                        nodes.append(
                            GraphNode(
                                id=influencer_id,
                                type="author",
                                label=influencer["name"],
                                metadata=NodeMetadata(
                                    birth_year=influencer.get("birth_year"),
                                    death_year=influencer.get("death_year"),
                                ),
                            )
                        )
                    edges.append(
                        GraphEdge(source=influencer_id, target=author_id, type="influenced")
                    )

                # Authors influenced by this one
                influenced_query = f"""
                    SELECT a.* FROM authors a
                    JOIN author_influences ai ON a.id = ai.influenced_id
                    WHERE ai.influencer_id = {adapter.placeholder}
                """
                influenced = adapter.fetchall(influenced_query, (author_id,))

                for influenced_author in influenced:
                    influenced_id = influenced_author["id"]
                    if influenced_id not in seen_authors:
                        seen_authors.add(influenced_id)
                        nodes.append(
                            GraphNode(
                                id=influenced_id,
                                type="author",
                                label=influenced_author["name"],
                                metadata=NodeMetadata(
                                    birth_year=influenced_author.get("birth_year"),
                                    death_year=influenced_author.get("death_year"),
                                ),
                            )
                        )
                    edges.append(
                        GraphEdge(source=author_id, target=influenced_id, type="influenced")
                    )

            return Graph(nodes=nodes, edges=edges)

        finally:
            adapter.close()

    @strawberry.field
    def search_authors(self, query: str, limit: int = 10) -> list[Author]:
        """
        Search for authors by name.

        Args:
            query: Search term (partial name matching)
            limit: Maximum number of results to return

        Returns:
            List of matching authors
        """
        adapter = get_adapter()
        adapter.connect()

        try:
            search_query = f"""
                SELECT * FROM authors
                WHERE name ILIKE {adapter.placeholder}
                ORDER BY name
                LIMIT {adapter.placeholder}
            """
            results = adapter.fetchall(search_query, (f"%{query}%", limit))

            return [
                Author(
                    id=row["id"],
                    name=row["name"],
                    first_name=row.get("first_name"),
                    last_name=row.get("last_name"),
                    birth_year=row.get("birth_year"),
                    death_year=row.get("death_year"),
                    birth_place=row.get("birth_place"),
                    nationality=row.get("nationality"),
                    bio=row.get("bio"),
                    wikidata_id=row.get("wikidata_id"),
                    viaf_id=row.get("viaf_id"),
                )
                for row in results
            ]

        finally:
            adapter.close()

    @strawberry.field
    def author(self, id: str) -> Author | None:
        """
        Get a single author by ID.

        Args:
            id: Author ID

        Returns:
            Author or None if not found
        """
        adapter = get_adapter()
        adapter.connect()

        try:
            query = f"SELECT * FROM authors WHERE id = {adapter.placeholder}"
            row = adapter.fetchone(query, (id,))

            if not row:
                return None

            return Author(
                id=row["id"],
                name=row["name"],
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                birth_year=row.get("birth_year"),
                death_year=row.get("death_year"),
                birth_place=row.get("birth_place"),
                nationality=row.get("nationality"),
                bio=row.get("bio"),
                wikidata_id=row.get("wikidata_id"),
                viaf_id=row.get("viaf_id"),
            )

        finally:
            adapter.close()

    @strawberry.field
    def book(self, id: str) -> Book | None:
        """
        Get a single book by ID.

        Args:
            id: Book ID

        Returns:
            Book or None if not found
        """
        adapter = get_adapter()
        adapter.connect()

        try:
            query = f"SELECT * FROM books WHERE id = {adapter.placeholder}"
            row = adapter.fetchone(query, (id,))

            if not row:
                return None

            return Book(
                id=row["id"],
                title=row["title"],
                publication_year=row.get("publication_year"),
                date_read=row.get("date_read"),
                isbn_13=row.get("isbn_13"),
                isbn_10=row.get("isbn_10"),
                openlibrary_id=row.get("openlibrary_id"),
                wikidata_id=row.get("wikidata_id"),
            )

        finally:
            adapter.close()
