"""Substitution boundaries for agent execution and catalog retrieval."""

from typing import Protocol
from uuid import UUID

from emporio_music_backend.contracts import (
    AgentResponse,
    ChatRequest,
    ConversationSession,
    ConversationSnapshot,
    CustomerIdentity,
    ExecutionContext,
    HistoryLimits,
    ProductSearchQuery,
    ProductSearchResult,
)
from emporio_music_backend.contracts.orders import (
    OrderDetail,
    OrderListQuery,
    OrderListResult,
    OrderLookupQuery,
)


class CustomerRepository(Protocol):
    def exists(self, identity: CustomerIdentity) -> bool:
        """Check the current imported customer registry; faults are explicit."""
        ...


class OrderRepository(Protocol):
    def list_orders(
        self, identity: CustomerIdentity, query: OrderListQuery
    ) -> OrderListResult:
        """Return only this known customer's bounded, newest-first orders."""
        ...

    def get_order(
        self, identity: CustomerIdentity, query: OrderLookupQuery
    ) -> OrderDetail | None:
        """Return an owned order; unknown and foreign IDs both return None.

        Unknown customers fail authorization. Storage faults never mean no match.
        """
        ...


class CustomerIdentityResolver(Protocol):
    def resolve(self, credential: str | None) -> CustomerIdentity:
        """Resolve a server-configured identity or raise AuthenticationError.

        A credential is supplied by the transport boundary, never model input.
        No credential is retained in the returned identity or execution context.
        """
        ...


class ConversationRepository(Protocol):
    """Short, synchronous local operations; append commits one complete turn."""

    def create(self, identity: CustomerIdentity) -> ConversationSession: ...

    def load(
        self, session_id: UUID, identity: CustomerIdentity, *, limits: HistoryLimits
    ) -> ConversationSnapshot: ...

    def append(
        self,
        session: ConversationSession,
        *,
        user_message: str,
        answer: str,
    ) -> None:
        """Atomically append or raise access or persistence error."""
        ...


class AgentExecutor(Protocol):
    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        """Execute with trusted, application-owned context; translate provider faults."""
        ...


class ProductRepository(Protocol):
    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
        """Return bounded ordered matches and the total before limiting.

        Apply category/name filters together, inclusive payable-price bounds, and
        active/positive-stock availability when requested. Unknown categories
        and unmatched names return an empty result; multiple matches are kept.
        Raise ProductRetrievalError for operational failures rather than
        substituting an empty result.
        """
        ...
