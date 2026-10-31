"""Substitution boundaries for agent execution and catalog retrieval."""

from typing import Protocol

from emporio_music_backend.contracts import (
    ChatRequest,
    ChatResponse,
    CustomerIdentity,
    ExecutionContext,
    ProductSearchQuery,
    ProductSearchResult,
)


class CustomerIdentityResolver(Protocol):
    def resolve(self, credential: str | None) -> CustomerIdentity:
        """Resolve a server-configured identity or raise AuthenticationError.

        A credential is supplied by the transport boundary, never model input.
        No credential is retained in the returned identity or execution context.
        """
        ...


class AgentExecutor(Protocol):
    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        """Execute with trusted, application-owned context; translate provider faults."""
        ...


class ProductRepository(Protocol):
    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
        """Return bounded ordered matches and the total before limiting.

        Apply category and name filters together, inclusive price bounds, and
        active/positive-stock availability when requested. Unknown categories
        and unmatched names return an empty result; multiple matches are kept.
        Raise ProductRetrievalError for operational failures rather than
        substituting an empty result.
        """
        ...
