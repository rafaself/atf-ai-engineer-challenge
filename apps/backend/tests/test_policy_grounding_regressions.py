"""US-17 trace regressions: scripted models verify contracts, not LLM quality."""

import asyncio
import json
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.api.app import create_app
from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.contracts.chat import ChatRequest
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.contracts.policies import PolicyExcerpt, PolicySearchResult
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music_backend.paths import DATA_DIRECTORY
from emporio_music_backend.policy_corpus import PolicyCorpus


class SourcePolicySearch:
    """Controlled evidence from the real corpus; does not measure retrieval."""

    def __init__(self, sections: set[str]) -> None:
        corpus = PolicyCorpus.model_validate_json(
            (DATA_DIRECTORY / "policies/corpus.json").read_text()
        )
        self.records: list[PolicyExcerpt] = [
            {
                "id": chunk.id,
                "source": corpus.source,
                "section": chunk.section,
                "hierarchy": chunk.hierarchy,
                "pages": chunk.pages,
                "text": chunk.text,
            }
            for chunk in corpus.chunks
            if chunk.section in sections
        ]
        self.queries: list[str] = []

    def search(self, query: str) -> PolicySearchResult:
        self.queries.append(query)
        return {"status": "evidence_found", "records": self.records}


def test_latest_qwen_answer_gets_deterministic_imported_snapshot_notice() -> None:
    run = json.loads(
        (
            DATA_DIRECTORY.parent / "docs/examples/us-18/mixed-final-qwen.json"
        ).read_text()
    )["runs"][0]
    messages = ModelMessagesTypeAdapter.validate_python(run["messages"])
    for message in messages:
        message.run_id = "recorded-current"
    answer = next(
        part.content
        for message in reversed(messages)
        for part in message.parts
        if isinstance(part, TextPart)
    )
    context = RunContext(
        deps=ExecutionContext(identity=CustomerIdentity(customer_id=1)),
        model=TestModel(),
        usage=RunUsage(),
        prompt=run["prompt"],
        run_id="recorded-current",
        messages=messages,
    )

    notice = (
        "Os dados dos pedidos vêm de uma fotografia importada, não de uma "
        "confirmação em tempo real. A previsão de entrega, se informada, não "
        "confirma a data real de recebimento."
    )
    accepted = customer_answer(context, answer)
    assert accepted.startswith(f"{answer}\n\n{notice}")
    assert "Fontes consultadas:" in accepted
    assert 'O pedido 4 está listado como "entregue"' in accepted
    assert "data real de recebimento não está disponível" in accepted
    assert "previsão de entrega" in accepted
    assert "não confirma a data real de recebimento" in accepted

    # Replaying an answer that already carries the application notice must not
    # append the same notice twice.
    assert customer_answer(context, accepted) == accepted


@pytest.mark.parametrize(
    ("tool_name", "content", "expected_notice"),
    [
        (
            "get_my_order",
            {"data_basis": "imported_snapshot", "order": {"order_id": 4}},
            True,
        ),
        (
            "list_my_orders",
            {
                "data_basis": "imported_snapshot",
                "orders": [{"order_id": 4}],
            },
            True,
        ),
        (
            "get_my_order",
            {"data_basis": "imported_snapshot", "order": None},
            False,
        ),
        (
            "list_my_orders",
            {"data_basis": "imported_snapshot", "orders": []},
            False,
        ),
    ],
)
def test_order_snapshot_notice_requires_nonempty_current_order_data(
    tool_name: str,
    content: dict[str, object],
    expected_notice: bool,
) -> None:
    context = RunContext(
        deps=ExecutionContext(identity=CustomerIdentity(customer_id=1)),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(parts=[ToolReturnPart(tool_name, content)], run_id="current")
        ],
    )
    answer = customer_answer(context, "Aqui estão os pedidos encontrados.")
    assert ("fotografia importada" in answer) is expected_notice


def test_order_snapshot_notice_ignores_previous_run_results() -> None:
    context = RunContext(
        deps=ExecutionContext(identity=CustomerIdentity(customer_id=1)),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "get_my_order",
                        {
                            "data_basis": "imported_snapshot",
                            "order": {"order_id": 4},
                        },
                    )
                ],
                run_id="previous",
            )
        ],
    )
    answer = "Aqui estão os pedidos encontrados."
    assert customer_answer(context, answer) == answer


def test_mixed_answer_can_correctly_discuss_the_recorded_claims(
    tmp_path: Path,
    operational_database: Path,
    demo_customer: dict[str, int],
) -> None:
    policy = SourcePolicySearch({"4.1", "4.3"})
    requests = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal requests
        requests += 1
        returned_tools = {
            part.tool_name
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        }
        if "get_my_order" not in returned_tools:
            return ModelResponse(parts=[ToolCallPart("get_my_order", {"order_id": 4})])
        if "search_store_policies" not in returned_tools:
            return ModelResponse(parts=[ToolCallPart("search_store_policies", {})])

        order_result = cast(
            dict[str, object],
            next(
                part.content
                for message in messages
                for part in message.parts
                if isinstance(part, ToolReturnPart) and part.tool_name == "get_my_order"
            ),
        )
        order = cast(dict[str, object], order_result["order"])
        assert order["status"] == "delivered"
        policy_result = cast(
            dict[str, object],
            next(
                part.content
                for message in messages
                for part in message.parts
                if isinstance(part, ToolReturnPart)
                and part.tool_name == "search_store_policies"
            ),
        )
        records = cast(list[dict[str, object]], policy_result["records"])
        assert {record["section"] for record in records} == {
            "4.1",
            "4.3",
        }
        answer = (
            "O pedido 4 consta como entregue na fotografia. A frase ‘foi entregue "
            "conforme o prazo estimado’ não é confirmada pelo registro; a previsão "
            "não informa o recebimento real. Para arrependimento online, a seção "
            "4.1 permite solicitar a devolução em até sete dias corridos após o "
            "recebimento; o produto deve estar na embalagem original, sem sinais "
            "de uso, com acessórios e manuais [política 4.1, p. 4]. A expressão "
            "‘perfeito estado’ aparece na seção 4.3, sobre troca por preferência, "
            "não como condição da devolução online [política 4.3, p. 4]. Qual foi "
            "o canal da compra, a data real de recebimento e a condição do instrumento?"
        )
        return ModelResponse(parts=[TextPart(answer)])

    historical = json.loads(
        (DATA_DIRECTORY.parent / "docs/examples/us-17/captures.json").read_text()
    )
    prompt = next(
        run["prompt"]
        for run in historical["runs"]
        if run["case_id"] == "mixed-order-return" and run["mode"] == "rag"
    )
    agent = create_store_agent(
        AgentSettings(),
        SQLiteProductRepository(
            operational_database.parent / "operational-catalog.sqlite3"
        ),
        SQLiteOrderRepository(operational_database),
        model=FunctionModel(respond),
        policy_search=policy,
    )
    repository = SQLiteConversationRepository(tmp_path / "chat.sqlite3")
    with TestClient(create_app(ChatService(agent, repository))) as client:
        response = client.post("/api/chat", json={**demo_customer, "message": prompt})

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "O pedido 4 consta como entregue na fotografia." in answer
    assert "[política 4.1, p. 4]" in answer
    assert "[política 4.3, p. 4]" in answer
    assert "fotografia importada" in answer
    assert requests == 3


@pytest.mark.parametrize("identity", [None, CustomerIdentity(customer_id=1)])
def test_order_return_without_id_allows_clarification(
    identity: CustomerIdentity | None,
    operational_database: Path,
) -> None:
    def clarify(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("Qual é o número do pedido?")])

    agent = create_store_agent(
        AgentSettings(),
        SQLiteProductRepository(
            operational_database.parent / "operational-catalog.sqlite3"
        ),
        SQLiteOrderRepository(operational_database),
        model=FunctionModel(clarify),
        policy_search=SourcePolicySearch({"4.1"}),
    )
    result = asyncio.run(
        agent.run(
            ChatRequest(message="Quero devolver meu pedido."),
            context=ExecutionContext(identity=identity),
        )
    )
    assert result.answer == "Qual é o número do pedido?"


def test_recorded_qwen_candidate_is_delivered_without_citation_retry(
    tmp_path: Path, operational_database: Path, demo_customer: dict[str, int]
) -> None:
    report = json.loads(
        (
            DATA_DIRECTORY.parent / "docs/examples/us-18/grounding-batch-qwen.json"
        ).read_text()
    )
    run = report["runs"][0]
    recorded = ModelMessagesTypeAdapter.validate_python(run["messages"])
    candidate = next(
        part.content
        for message in reversed(recorded)
        for part in reversed(message.parts)
        if isinstance(part, TextPart)
    )
    requests = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal requests
        requests += 1
        returned = {
            part.tool_name
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        }
        if "get_my_order" not in returned:
            return ModelResponse(parts=[ToolCallPart("get_my_order", {"order_id": 4})])
        if "search_store_policies" not in returned:
            return ModelResponse(parts=[ToolCallPart("search_store_policies", {})])
        return ModelResponse(parts=[TextPart(candidate)])

    policy = SourcePolicySearch({"4.1", "4.3", "4.4", "5.2"})
    agent = create_store_agent(
        AgentSettings(),
        SQLiteProductRepository(
            operational_database.parent / "operational-catalog.sqlite3"
        ),
        SQLiteOrderRepository(operational_database),
        model=FunctionModel(respond),
        policy_search=policy,
    )
    repository = SQLiteConversationRepository(tmp_path / "history.sqlite3")
    with TestClient(create_app(ChatService(agent, repository))) as client:
        response = client.post(
            "/api/chat", json={**demo_customer, "message": run["prompt"]}
        )
    assert response.status_code == 200
    assert response.json()["answer"].startswith(candidate.strip())
    assert "Fontes consultadas:" in response.json()["answer"]
    assert "seção 4.1, p. 4" in response.json()["answer"]
    assert requests == 3
