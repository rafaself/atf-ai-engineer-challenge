"""Policy-only and mixed policy/order tool behavior through the existing agent."""

import asyncio
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from emporio_music_backend.agent.factory import PydanticAgentExecutor
from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.policies import PolicySearchPort
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.api.app import create_app
from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.contracts.catalog import (
    ProductSearchQuery,
    ProductSearchResult,
)
from emporio_music_backend.contracts.chat import ChatRequest
from emporio_music_backend.contracts.conversations import (
    ConversationMessage,
    ConversationSession,
    ExecutionContext,
)
from emporio_music_backend.contracts.errors import PolicyRetrievalError
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.contracts.orders import (
    OrderDetail,
    OrderListQuery,
    OrderListResult,
    OrderLookupQuery,
)
from emporio_music_backend.contracts.policies import PolicySearchResult
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.ports.orders import OrderRepository


class UnusedProducts:
    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
        raise AssertionError("This scenario does not ask about catalog products")


class FixedOrders:
    def __init__(self) -> None:
        self.identities: list[CustomerIdentity] = []

    def list_orders(
        self, identity: CustomerIdentity, query: OrderListQuery
    ) -> OrderListResult:
        self.identities.append(identity)
        return OrderListResult()

    def get_order(
        self, identity: CustomerIdentity, query: OrderLookupQuery
    ) -> OrderDetail | None:
        self.identities.append(identity)
        return OrderDetail(
            order_id=query.order_id,
            order_date=date(2026, 10, 30),
            status="pending",
            total_centavos=69900,
        )


class FixedPolicySearch:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.result: PolicySearchResult = {
            "status": "evidence_found",
            "records": [
                {
                    "id": "policy-v2.1-s4.1",
                    "source": "store_policies.pdf",
                    "section": "4.1",
                    "hierarchy": [
                        "4 Política de Trocas e Devoluções",
                        "4.1 Direito de Arrependimento",
                    ],
                    "pages": [4],
                    "text": "Para compras online, o prazo conta do recebimento.",
                }
            ],
        }

    def search(self, query: str) -> PolicySearchResult:
        self.queries.append(query)
        return self.result


def _store_agent(
    model: FunctionModel,
    policy_search: PolicySearchPort,
    orders: OrderRepository | None = None,
) -> PydanticAgentExecutor:
    return create_store_agent(
        AgentSettings(),
        UnusedProducts(),
        orders or FixedOrders(),
        model=model,
        policy_search=policy_search,
    )


def test_mixed_policy_and_order_question_uses_both_tools_with_current_query() -> None:
    policy = FixedPolicySearch()
    orders = FixedOrders()
    called: list[str] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        names = {tool.name for tool in info.function_tools}
        assert "search_store_policies" in names and "get_my_order" in names
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            called.append("search_store_policies")
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "search_store_policies",
                        {"query": "Meu pedido pode ser devolvido?"},
                    )
                ]
            )
        if returns[-1].tool_name == "search_store_policies":
            called.append("get_my_order")
            return ModelResponse(parts=[ToolCallPart("get_my_order", {"order_id": 7})])
        return ModelResponse(
            parts=[
                TextPart(
                    "Vou verificar a condição do manual e o status do pedido. "
                    "[política 4.1, p. 4]"
                )
            ]
        )

    agent = _store_agent(FunctionModel(respond), policy, orders)
    identity = CustomerIdentity(customer_id=1)
    context = ExecutionContext(
        identity=identity,
        session=ConversationSession(owner=identity),
        history=(
            ConversationMessage(
                role="user", content="Antes perguntei sobre empréstimo."
            ),
            ConversationMessage(
                role="assistant", content="Não encontrei essa informação."
            ),
        ),
    )

    result = asyncio.run(
        agent.run(
            ChatRequest(message="Meu pedido pode ser devolvido?"), context=context
        )
    )

    assert result.answer.endswith("[política 4.1, p. 4]")
    assert called == ["search_store_policies", "get_my_order"]
    assert policy.queries == ["Meu pedido pode ser devolvido?"]
    assert orders.identities == [identity]


def test_post_chat_can_answer_policy_question_with_source_reference(
    tmp_path: Path,
) -> None:
    policy = FixedPolicySearch()

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not any(
            isinstance(part, ToolReturnPart)
            for message in messages
            for part in message.parts
        ):
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "search_store_policies",
                        {"query": "Qual o prazo para arrependimento?"},
                    )
                ]
            )
        return ModelResponse(
            parts=[
                TextPart(
                    "Para compras online, consulte o prazo contado do recebimento. [política 4.1, p. 4]"
                )
            ]
        )

    agent = _store_agent(FunctionModel(respond), policy)
    service = ChatService(
        agent, SQLiteConversationRepository(tmp_path / "chat.sqlite3")
    )
    with TestClient(create_app(service)) as client:
        response = client.post(
            "/api/chat", json={"message": "Qual o prazo para arrependimento?"}
        )
    assert response.status_code == 200
    assert "[política 4.1, p. 4]" in response.json()["answer"]
    assert policy.queries == ["Qual o prazo para arrependimento?"]


def test_uncertain_return_eligibility_response_keeps_source_and_missing_facts() -> None:
    policy = FixedPolicySearch()
    policy.result["records"].append(
        {
            "id": "policy-v2.1-s4.4",
            "source": "store_policies.pdf",
            "section": "4.4",
            "hierarchy": [
                "4 Política de Trocas e Devoluções",
                "4.4 Itens Não Elegíveis para Troca",
            ],
            "pages": [4],
            "text": "Exclusões: personalização, venda final e boquilhas.",
        }
    )

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not any(
            isinstance(part, ToolReturnPart)
            for message in messages
            for part in message.parts
        ):
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "search_store_policies",
                        {"query": "Comprei há uma semana, posso devolver?"},
                    )
                ]
            )
        return ModelResponse(
            parts=[
                TextPart(
                    "Não consigo confirmar a elegibilidade apenas pela data da compra. "
                    "Você comprou online e em que dia recebeu? O produto está na "
                    "embalagem original, sem sinais de uso e com acessórios e manuais? "
                    "Ele é personalizado, de venda final ou uma boquilha? "
                    "[política 4.1, p. 4] [política 4.4, p. 4]"
                )
            ]
        )

    agent = _store_agent(FunctionModel(respond), policy)
    result = asyncio.run(
        agent.run(
            ChatRequest(message="Comprei há uma semana, posso devolver?"),
            context=ExecutionContext(),
        )
    )

    assert "Não consigo confirmar a elegibilidade" in result.answer
    assert "em que dia recebeu" in result.answer
    assert "acessórios e manuais" in result.answer
    assert "[política 4.1, p. 4] [política 4.4, p. 4]" in result.answer


def test_policy_tool_failure_propagates_instead_of_becoming_no_match() -> None:
    class FailedSearch:
        def search(self, query: str) -> PolicySearchResult:
            raise PolicyRetrievalError("private index failure")

    def call_policy(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart("search_store_policies", {"query": "Qual o horário?"})]
        )

    agent = _store_agent(FunctionModel(call_policy), FailedSearch())
    with pytest.raises(PolicyRetrievalError, match="private index failure"):
        asyncio.run(
            agent.run(
                ChatRequest(message="Qual o horário?"), context=ExecutionContext()
            )
        )
