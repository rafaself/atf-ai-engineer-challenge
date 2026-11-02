"""Read-only tools with customer scope supplied exclusively by per-run dependencies."""

from typing import Annotated

from pydantic import Field
from pydantic_ai import RunContext, Tool
from pydantic_ai.models import Model

from emporio_music_backend.agent.catalog import product_tools
from emporio_music_backend.agent.factory import PydanticAgentExecutor, create_agent
from emporio_music_backend.agent.policies import (
    LocalPolicySearch,
    PolicySearchPort,
    policy_tools,
)
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.orders import (
    DatabaseId,
    OrderListQuery,
    OrderLookupQuery,
)
from emporio_music_backend.diagnostics import trace
from emporio_music_backend.ports.catalog import ProductRepository
from emporio_music_backend.ports.orders import OrderRepository


class OrderTools:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    def list_my_orders(
        self,
        ctx: RunContext[ExecutionContext],
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 5,
    ) -> dict[str, object]:
        """List orders in the selected demo account, newest first (imported snapshot).

        Args:
            limit: Maximum orders to return, 1–20, default 5. Not a customer scope.
        """
        identity = ctx.deps.identity
        if identity is None:
            return {
                "customer_selection_required": True,
                "message": "Selecione um cliente fictício da demonstração para consultar pedidos.",
            }
        trace("tool.called", tool="list_my_orders", limit=limit)
        result = self.repository.list_orders(identity, OrderListQuery(limit=limit))
        return {**result.model_dump(mode="json"), "data_basis": "imported_snapshot"}

    def get_my_order(
        self, ctx: RunContext[ExecutionContext], order_id: DatabaseId
    ) -> dict[str, object]:
        """Read an order in the selected demo account, with at most 20 items.

        Missing and inaccessible orders have the same not-found response. Tracking
        and estimated delivery reflect an import, not a live carrier consultation.
        Args:
            order_id: Positive order identifier to look up within your account.
        """
        identity = ctx.deps.identity
        if identity is None:
            return {
                "customer_selection_required": True,
                "message": "Selecione um cliente fictício da demonstração para consultar pedidos.",
            }
        trace("tool.called", tool="get_my_order")
        order = self.repository.get_order(identity, OrderLookupQuery(order_id=order_id))
        return {
            "order": order.model_dump(mode="json") if order is not None else None,
            "message": None
            if order is not None
            else "Pedido não encontrado na sua conta.",
            "data_basis": "imported_snapshot",
            **(
                {
                    "answer_guidance": [
                        "estimated_delivery é somente previsão: não diga que o pedido foi entregue "
                        "nessa data ou conforme esse prazo. O snapshot não informa data real de "
                        "recebimento, canal da compra nem condição do produto. Para devolução, "
                        "chame search_store_policies agora, antes de perguntar esses três fatos. "
                        "Não espere respostas do cliente para consultar a política nesta rodada."
                    ]
                }
                if order is not None
                else {}
            ),
        }


def create_store_agent(
    settings: AgentSettings,
    products: ProductRepository,
    orders: OrderRepository,
    *,
    model: Model | None = None,
    policy_search: PolicySearchPort | None = None,
) -> PydanticAgentExecutor:
    tools = OrderTools(orders)
    if policy_search is None:
        policy_search = LocalPolicySearch()
    return create_agent(
        settings,
        model=model,
        tools=[
            *product_tools(products),
            Tool(tools.list_my_orders),
            Tool(tools.get_my_order),
            *policy_tools(policy_search),
        ],
    )
