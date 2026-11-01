"""Read-only tools with customer scope supplied exclusively by per-run dependencies."""

from typing import Annotated

from pydantic import Field
from pydantic_ai import RunContext, Tool
from pydantic_ai.models import Model

from emporio_music_backend.agent.catalog import product_tools
from emporio_music_backend.agent.factory import PydanticAgentExecutor, create_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.errors import AuthenticationError
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.contracts.orders import (
    DatabaseId,
    OrderListQuery,
    OrderLookupQuery,
)
from emporio_music_backend.diagnostics import trace
from emporio_music_backend.ports.catalog import ProductRepository
from emporio_music_backend.ports.orders import OrderRepository


def _identity(ctx: RunContext[ExecutionContext]) -> CustomerIdentity:
    if ctx.deps.identity is None:
        raise AuthenticationError("Customer identity required")
    return ctx.deps.identity


class OrderTools:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    def list_my_orders(
        self,
        ctx: RunContext[ExecutionContext],
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 5,
    ) -> dict[str, object]:
        """List orders in the authenticated account, newest first (imported snapshot).

        Args:
            limit: Maximum orders to return, 1–20, default 5. Not a customer scope.
        """
        identity = _identity(ctx)
        trace("tool.called", tool="list_my_orders", limit=limit)
        result = self.repository.list_orders(identity, OrderListQuery(limit=limit))
        return {**result.model_dump(mode="json"), "data_basis": "imported_snapshot"}

    def get_my_order(
        self, ctx: RunContext[ExecutionContext], order_id: DatabaseId
    ) -> dict[str, object]:
        """Read an order in the authenticated account, with at most 20 items.

        Missing and inaccessible orders have the same not-found response. Tracking
        and estimated delivery reflect an import, not a live carrier consultation.
        Args:
            order_id: Positive order identifier to look up within your account.
        """
        identity = _identity(ctx)
        trace("tool.called", tool="get_my_order")
        order = self.repository.get_order(identity, OrderLookupQuery(order_id=order_id))
        return {
            "order": order.model_dump(mode="json") if order is not None else None,
            "message": None
            if order is not None
            else "Pedido não encontrado na sua conta.",
            "data_basis": "imported_snapshot",
        }


def create_store_agent(
    settings: AgentSettings,
    products: ProductRepository,
    orders: OrderRepository,
    *,
    model: Model | None = None,
) -> PydanticAgentExecutor:
    tools = OrderTools(orders)
    return create_agent(
        settings,
        model=model,
        tools=[
            *product_tools(products),
            Tool(tools.list_my_orders),
            Tool(tools.get_my_order),
        ],
    )
