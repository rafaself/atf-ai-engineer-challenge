"""Substitution boundaries for agent execution and catalog retrieval."""

from typing import Protocol

from emporio_music_backend.contracts import (
    ChatRequest,
    ChatResponse,
    ProductSearchQuery,
    ProductSearchResult,
)


class AgentExecutor(Protocol):
    async def run(self, request: ChatRequest) -> ChatResponse:
        """Execute a single message; adapters translate provider failures."""
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
