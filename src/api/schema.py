"""GraphQL schema combining all types and resolvers."""

import strawberry

from api.resolvers.graph import Query

schema = strawberry.Schema(query=Query)
