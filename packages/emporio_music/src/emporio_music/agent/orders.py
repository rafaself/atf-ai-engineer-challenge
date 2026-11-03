"""Read-only tools with customer scope supplied exclusively by per-run dependencies."""

from datetime import date
from typing import Annotated

from pydantic import Field
from pydantic_ai import RunContext, Tool
from pydantic_ai.models import Model

from emporio_music.agent.catalog import product_tools
from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.factory import create_agent
from emporio_music.agent.policies import policy_tools
from emporio_music.agent.settings import AgentSettings
from emporio_music.application.deadlines import (
    calculate_deadline as calculate_policy_deadline,
)
from emporio_music.diagnostics import trace
from emporio_music.domain.base import NonblankText
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.deadlines import (
    DeadlineEvent,
    DeadlineRequest,
    DeadlineType,
    DeliveryDestination,
    DeliveryService,
)
from emporio_music.domain.errors import (
    AmbiguousTrackingCodeError,
    ConfigurationError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.orders import (
    DatabaseId,
    OrderDetail,
    OrderListQuery,
    OrderLookupQuery,
    OrderTrackingCodeQuery,
)
from emporio_music.policies.search import LocalPolicySearch
from emporio_music.ports.catalog import ProductRepository
from emporio_music.ports.orders import OrderRepository
from emporio_music.ports.policies import PolicySearchPort


class OrderTools:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    def list_my_orders(
        self,
        ctx: RunContext[ExecutionContext],
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 5,
    ) -> dict[str, object]:
        """List orders in the fixed demo account, newest first (current simulated API result).

        Args:
            limit: Maximum orders to return, 1–20, default 5. Not a customer scope.
        """
        identity = self._identity(ctx)
        trace("tool.called", tool="list_my_orders", limit=limit)
        result = self.repository.list_orders(identity, OrderListQuery(limit=limit))
        return {**result.model_dump(mode="json"), "data_basis": "simulated_current"}

    def get_my_order(
        self, ctx: RunContext[ExecutionContext], order_id: DatabaseId
    ) -> dict[str, object]:
        """Read an order in the fixed demo account, with at most 20 items.

        Call again for follow-up questions about items, quantities, status or tracking,
        using the order_id from the preceding list or conversation. The order record
        does not contain purchase channel, actual receipt date or product condition;
        ask the customer for those facts when assessing return eligibility.
        Missing and inaccessible orders have the same not-found response. Tracking
        is the simulated system record; estimated delivery is not an actual receipt date.
        Args:
            order_id: Positive order identifier to look up within your account.
        """
        identity = self._identity(ctx)
        trace("tool.called", tool="get_my_order")
        order = self.repository.get_order(identity, OrderLookupQuery(order_id=order_id))
        return self._order_result(order, "Pedido não encontrado na sua conta.")

    def get_my_order_by_tracking_code(
        self, ctx: RunContext[ExecutionContext], tracking_code: NonblankText
    ) -> dict[str, object]:
        """Read the owned order for an exact tracking code from the current snapshot.

        The stored code and delivery estimate are simulated records, not live carrier
        status or confirmation of receipt. Foreign and unknown codes have one result.
        If several owned orders share the code, ask for an order ID instead.
        Args:
            tracking_code: Nonblank tracking code supplied by the customer.
        """
        identity = self._identity(ctx)
        trace("tool.called", tool="get_my_order_by_tracking_code")
        try:
            order = self.repository.get_order_by_tracking_code(
                identity,
                OrderTrackingCodeQuery(tracking_code=tracking_code),
            )
        except AmbiguousTrackingCodeError:
            return {
                "order": None,
                "message": (
                    "Encontramos mais de um pedido com esse código de rastreamento "
                    "na sua conta. Informe o número do pedido para continuar."
                ),
                "data_basis": "simulated_current",
            }
        return self._order_result(
            order,
            "Não encontramos nenhum pedido com esse código de rastreamento na sua conta.",
        )

    @staticmethod
    def _identity(ctx: RunContext[ExecutionContext]) -> CustomerIdentity:
        identity = ctx.deps.identity
        if identity is None:
            raise ConfigurationError("The fixed demo identity is unavailable")
        return identity

    @staticmethod
    def _order_result(
        order: OrderDetail | None, not_found_message: str
    ) -> dict[str, object]:
        if order is not None:
            return {
                "order": order.model_dump(mode="json"),
                "message": None,
                "data_basis": "simulated_current",
                "answer_guidance": [
                    "Este é o registro atual da API simulada. A previsão de entrega "
                    "não confirma o recebimento real. Se a pergunta também envolve "
                    "políticas, consulte search_store_policies antes de responder. "
                    "O registro não contém canal de compra, data de recebimento real "
                    "ou condição física do produto; confirme esses fatos com o cliente "
                    "antes de avaliar uma devolução."
                ],
            }
        return {
            "order": None,
            "message": not_found_message,
            "data_basis": "simulated_current",
        }

    def calculate_deadline(
        self,
        ctx: RunContext[ExecutionContext],
        deadline_type: DeadlineType,
        order_id: DatabaseId | None = None,
        reference_date: date | None = None,
        reference_event: DeadlineEvent | None = None,
        request_date: date | None = None,
        destination: DeliveryDestination | None = None,
        delivery_service: DeliveryService | None = None,
    ) -> dict[str, object]:
        """Calculate or qualify a supported order/policy deadline.

        A stored estimated delivery date is only an estimate; it is never actual
        receipt. Online-return and legal-warranty calculations require the actual
        receipt event/date. Defect exchange uses the stored purchase date. Refund
        timing can only be stated as up to ten business days because the manual
        does not define its starting event. Delivery windows applied after a
        supplied dispatch date are conditional estimates; the manual does not
        explicitly establish dispatch as the start event. Business-day estimates
        exclude weekends and explicitly do not model holidays.

        Args:
            deadline_type: delivery, online_return, defect_exchange, refund, or warranty.
            order_id: Optional order ID to resolve from the fixed demo account.
            reference_date: A customer-reported purchase, dispatch, or actual receipt date.
            reference_event: Event that the supplied date represents; must match the deadline.
            request_date: Optional return/exchange/warranty request date for window assessment.
            destination: Required for a calculated delivery window if no stored estimate exists.
            delivery_service: PAC, SEDEX, or Jadlog for an outside-Campo-Grande estimate.
        """
        request = DeadlineRequest(
            deadline_type=deadline_type,
            order_id=order_id,
            reference_date=reference_date,
            reference_event=reference_event,
            request_date=request_date,
            destination=destination,
            delivery_service=delivery_service,
        )
        identity = self._identity(ctx)
        order = None
        if order_id is not None:
            trace("tool.called", tool="calculate_deadline", lookup="owned_order")
            order = self.repository.get_order(
                identity, OrderLookupQuery(order_id=order_id)
            )
        else:
            trace("tool.called", tool="calculate_deadline", lookup="policy_only")
        result = calculate_policy_deadline(
            request,
            order=order,
        )
        trace("tool.result", tool="calculate_deadline", status=result.status)
        return {
            **result.model_dump(mode="json"),
            "data_basis": "simulated_current",
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
            Tool(tools.get_my_order_by_tracking_code),
            Tool(tools.calculate_deadline),
            *policy_tools(policy_search),
        ],
    )
