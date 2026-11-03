"""Policy-only and mixed policy/order tool behavior through the existing agent."""

import asyncio
from datetime import date
from pathlib import Path
from typing import cast

import pytest
from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.policies import PolicyTools
from emporio_music.agent.settings import AgentSettings
from emporio_music.application.chat import ChatService
from emporio_music.domain.catalog import (
    ProductSearchQuery,
    ProductSearchResult,
)
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import (
    ConversationMessage,
    ConversationSession,
    ExecutionContext,
)
from emporio_music.domain.errors import (
    PolicyRetrievalError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.orders import (
    OrderDetail,
    OrderListQuery,
    OrderListResult,
    OrderLookupQuery,
)
from emporio_music.domain.policies import PolicySearchResult
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music.paths import DATA_DIRECTORY
from emporio_music.policies.corpus import prepare
from emporio_music.ports.orders import OrderRepository
from emporio_music.ports.policies import PolicySearchPort
from emporio_music_api.app import create_app
from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage


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

    def search(
        self, query: str, *, policy_scope: str = "general"
    ) -> PolicySearchResult:
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


def test_policy_tool_has_no_model_query_arguments() -> None:
    policy = FixedPolicySearch()
    prompt = "Meu pedido 4 consta como entregue. Confira o pedido e me diga se posso devolvê-lo agora."

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool = next(
            tool for tool in info.function_tools if tool.name == "search_store_policies"
        )
        assert set(tool.parameters_json_schema["properties"]) == {"policy_scope"}
        if not policy.queries:
            return ModelResponse(
                parts=[
                    ToolCallPart("search_store_policies", {"policy_scope": "general"})
                ]
            )
        return ModelResponse(
            parts=[TextPart("Preciso confirmar as condições [política 4.1, p. 4].")]
        )

    result = asyncio.run(
        _store_agent(FunctionModel(respond), policy).run(
            ChatRequest(message=prompt),
            context=ExecutionContext(),
        )
    )
    assert result.answer
    assert policy.queries == [prompt]


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
                    ToolCallPart("search_store_policies", {"policy_scope": "general"})
                ]
            )
        if returns[-1].tool_name == "search_store_policies":
            called.append("get_my_order")
            return ModelResponse(parts=[ToolCallPart("get_my_order", {"order_id": 7})])
        return ModelResponse(
            parts=[
                TextPart(
                    "O status vem de uma fotografia importada; preciso confirmar as condições. "
                    "[política 4.1, p. 4]"
                )
            ]
        )

    agent = _store_agent(FunctionModel(respond), policy, orders)
    identity = CustomerIdentity(customer_id=1)
    context = ExecutionContext(
        identity=identity, session=ConversationSession(owner=identity)
    )

    result = asyncio.run(
        agent.run(
            ChatRequest(message="Meu pedido pode ser devolvido?"), context=context
        )
    )

    assert result.answer.startswith("O status vem de uma fotografia importada")
    assert "[política 4.1, p. 4]" in result.answer
    assert "preciso confirmar as condições" in result.answer
    assert "Os dados dos pedidos vêm" not in result.answer
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
                    ToolCallPart("search_store_policies", {"policy_scope": "general"})
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


def test_follow_up_policy_search_includes_the_latest_prior_user_question(
    tmp_path: Path,
) -> None:
    policy = FixedPolicySearch()
    previous_question = "Quero saber as condições para devolver um instrumento."
    follow_up = "E se eu já usei o instrumento?"

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not any(
            isinstance(part, ToolReturnPart)
            and part.tool_name == "search_store_policies"
            for message in messages
            for part in message.parts
        ):
            return ModelResponse(
                parts=[
                    ToolCallPart("search_store_policies", {"policy_scope": "general"})
                ]
            )
        return ModelResponse(
            parts=[
                TextPart(
                    "O relato de uso não confirma sinais de uso. [política 4.1, p. 4]"
                )
            ]
        )

    service = ChatService(
        _store_agent(FunctionModel(respond), policy),
        SQLiteConversationRepository(tmp_path / "history.sqlite3"),
    )
    with TestClient(create_app(service)) as client:
        first = client.post("/api/chat", json={"message": previous_question})
        assert first.status_code == 200
        second = client.post(
            "/api/chat",
            json={"message": follow_up, "session_id": first.json()["session_id"]},
        )

    assert second.status_code == 200
    assert policy.queries == [
        previous_question,
        f"{previous_question}\n{follow_up}",
    ]


def test_long_policy_context_falls_back_to_the_current_question() -> None:
    policy = FixedPolicySearch()
    current_question = "E se eu já usei o instrumento?"
    context = ExecutionContext(
        session=ConversationSession(),
        history=(
            ConversationMessage(role="user", content="x" * 250),
            ConversationMessage(role="assistant", content="Resposta anterior."),
        ),
    )
    PolicyTools(policy).search_store_policies(
        RunContext(
            deps=context,
            model=TestModel(),
            usage=RunUsage(),
            prompt=current_question,
        ),
        policy_scope="general",
    )

    assert policy.queries == [current_question]


def test_invented_assistant_history_does_not_become_current_policy_evidence() -> None:
    policy = FixedPolicySearch()
    rule = next(
        c.online_return_rule
        for c in prepare(DATA_DIRECTORY / "store_policies.pdf").chunks
        if c.section == "4.1"
    )
    assert rule is not None
    policy.result["records"][0]["online_return_rule"] = rule
    prior_claim = "Envie fotos para sac@inventado.example; enviaremos sua etiqueta."
    question = "Como obtenho a etiqueta e quais documentos envio?"
    context = ExecutionContext(
        session=ConversationSession(),
        history=(
            ConversationMessage(
                role="user", content="Quero devolver uma compra online."
            ),
            ConversationMessage(role="assistant", content=prior_claim),
        ),
    )

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            assert any(
                isinstance(part, TextPart) and part.content == prior_claim
                for message in messages
                for part in message.parts
            )
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "search_store_policies", {"policy_scope": "online_return"}
                    )
                ]
            )
        assert returns[-1].tool_name == "search_store_policies"
        evidence = cast(PolicySearchResult, returns[-1].content)
        current_rule = evidence["records"][0]["online_return_rule"]
        assert current_rule["procedure"]["label_issuance"] == "not_specified_in_manual"
        assert (
            current_rule["procedure"]["required_documents"] == "not_specified_in_manual"
        )
        assert prior_claim not in str(evidence)
        return ModelResponse(
            parts=[
                TextPart(
                    "O manual não detalha os documentos nem a emissão de etiqueta. O frete de devolução por arrependimento é por conta da loja."
                )
            ]
        )

    result = asyncio.run(
        _store_agent(FunctionModel(respond), policy).run(
            ChatRequest(message=question), context=context
        )
    )
    assert "frete" in result.answer
    assert policy.queries == [f"Quero devolver uma compra online.\n{question}"]


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
                    ToolCallPart("search_store_policies", {"policy_scope": "general"})
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
        def search(
            self, query: str, *, policy_scope: str = "general"
        ) -> PolicySearchResult:
            raise PolicyRetrievalError("private index failure")

    def call_policy(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart("search_store_policies", {"policy_scope": "general"})]
        )

    agent = _store_agent(FunctionModel(call_policy), FailedSearch())
    with pytest.raises(PolicyRetrievalError, match="private index failure"):
        asyncio.run(
            agent.run(
                ChatRequest(message="Qual o horário?"), context=ExecutionContext()
            )
        )
