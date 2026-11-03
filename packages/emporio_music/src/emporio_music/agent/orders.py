"""Read-only tools with customer scope supplied exclusively by per-run dependencies."""

from typing import Annotated

from pydantic import Field
from pydantic_ai import RunContext, Tool
from pydantic_ai.models import Model

from emporio_music.agent.catalog import product_tools
from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.factory import create_agent
from emporio_music.agent.policies import policy_tools
from emporio_music.agent.settings import AgentSettings
from emporio_music.diagnostics import trace
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.orders import (
    DatabaseId,
    OrderListQuery,
    OrderLookupQuery,
)
from emporio_music.policies.search import LocalPolicySearch
from emporio_music.ports.catalog import ProductRepository
from emporio_music.ports.orders import OrderRepository
from emporio_music.ports.policies import PolicySearchPort


class OrderTools:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    async def list_my_orders(
        self,
        ctx: RunContext[ExecutionContext],
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 5,
    ) -> dict[str, object]:
        """List orders in the selected demo account, newest first (current simulated API result).

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
        return {**result.model_dump(mode="json"), "data_basis": "simulated_current"}

    async def get_my_order(
        self, ctx: RunContext[ExecutionContext], order_id: DatabaseId
    ) -> dict[str, object]:
        """Read an order in the selected demo account, with at most 20 items.

        Call again for follow-up questions about items, quantities, status or tracking,
        using the order_id from the preceding list or conversation. The order record
        does not contain purchase channel, actual receipt date or product condition;
        ask the customer for those facts when assessing return eligibility.
        Missing and inaccessible orders have the same not-found response. Tracking
        is the simulated system record; estimated delivery is not an actual receipt date.
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
            "data_basis": "simulated_current",
            **(
                {
                    "answer_guidance": [
                        "Este é o registro atual da API simulada. A previsão de entrega "
                        "não confirma o recebimento real. Se a pergunta também envolve "
                        "políticas, consulte search_store_policies antes de responder. "
                        "O registro não contém canal de compra, data de recebimento real "
                        "ou condição física do produto; confirme esses fatos com o cliente "
                        "antes de avaliar uma devolução."
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
