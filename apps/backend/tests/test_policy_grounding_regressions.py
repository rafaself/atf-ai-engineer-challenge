"""US-17 trace regressions: scripted models verify contracts, not LLM quality."""

import asyncio
import json
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.agent.policies import PolicyTools
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


def test_missing_policy_retry_requests_the_lookup_before_customer_clarification() -> (
    None
):
    run = json.loads(
        (
            DATA_DIRECTORY.parent / "docs/examples/us-18/mixed-current-question.json"
        ).read_text()
    )["runs"][0]
    messages = ModelMessagesTypeAdapter.validate_python(run["messages"])
    for message in messages:
        message.run_id = "recorded-current"
    context = RunContext(
        deps=ExecutionContext(identity=CustomerIdentity(customer_id=1)),
        model=TestModel(),
        usage=RunUsage(),
        prompt=run["prompt"],
        run_id="recorded-current",
        messages=messages,
    )
    answer = next(
        part.content
        for message in reversed(messages)
        for part in message.parts
        if isinstance(part, TextPart)
    )
    with pytest.raises(ModelRetry) as correction:
        customer_answer(context, answer)
    assert "search_store_policies" in str(correction.value)
    assert "AGORA" in str(correction.value)
    assert "Não espere" in str(correction.value)
    assert "preços/totais" not in str(correction.value)


def test_citation_retry_requests_rule_explanation_not_decorative_reference() -> None:
    run = json.loads(
        (
            DATA_DIRECTORY.parent / "docs/examples/us-18/mixed-targeted-feedback-2.json"
        ).read_text()
    )["runs"][0]
    messages = ModelMessagesTypeAdapter.validate_python(run["messages"])
    for message in messages:
        message.run_id = "recorded-current"
    answer = next(
        part.content
        for message in messages
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
    with pytest.raises(ModelRetry) as correction:
        customer_answer(context, answer)
    assert "Explique a regra" in str(correction.value)
    assert "Não cite política para fatos do pedido" in str(correction.value)


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
    assert accepted == f"{answer}\n\n{notice}"
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


def test_recorded_mixed_failure_is_corrected_through_http(
    tmp_path: Path,
    operational_database: Path,
    demo_customer: dict[str, int],
) -> None:
    captures = json.loads(
        (DATA_DIRECTORY.parent / "docs/examples/us-17/captures.json").read_text()
    )
    historical = next(
        run
        for run in captures["runs"]
        if run["case_id"] == "mixed-order-return" and run["mode"] == "rag"
    )
    policy = SourcePolicySearch({"4.1"})
    observed_tools: list[str] = []
    requests = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal requests
        requests += 1
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            observed_tools.append("get_my_order")
            return ModelResponse(parts=[ToolCallPart("get_my_order", {"order_id": 4})])
        if len(returns) == 1:
            order_result = returns[0].content
            assert isinstance(order_result, dict)
            assert order_result.get("data_basis") == "imported_snapshot"
            order = order_result.get("order")
            assert isinstance(order, dict)
            assert order.get("estimated_delivery") == "2025-12-22"
            if requests == 2:
                # Exact failed live answer must no longer escape as HTTP success.
                return ModelResponse(
                    parts=[TextPart(historical["http_response"]["answer"])]
                )
            feedback = messages[-1].parts[-1]
            assert isinstance(feedback, UserPromptPart)
            assert "search_store_policies AGORA" in str(feedback.content)
            observed_tools.append("search_store_policies")
            return ModelResponse(parts=[ToolCallPart("search_store_policies", {})])
        return ModelResponse(
            parts=[
                TextPart(
                    "O pedido consta como entregue na fotografia importada. A previsão "
                    "de entrega não confirma o recebimento real. Para compras online, "
                    "o prazo é de sete dias corridos do recebimento, com embalagem "
                    "original, sem sinais de uso e com acessórios e manuais "
                    "[política 4.1, p. 4]. Comprou online? Quando recebeu e qual o estado "
                    "do produto? Ainda não consigo confirmar a elegibilidade."
                )
            ]
        )

    repository = SQLiteConversationRepository(tmp_path / "chat.sqlite3")
    agent = create_store_agent(
        AgentSettings(),
        SQLiteProductRepository(
            operational_database.parent / "operational-catalog.sqlite3"
        ),
        SQLiteOrderRepository(operational_database),
        model=FunctionModel(respond),
        policy_search=policy,
    )
    with TestClient(create_app(ChatService(agent, repository))) as client:
        response = client.post(
            "/api/chat", json={**demo_customer, "message": historical["prompt"]}
        )
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "[política 4.1, p. 4]" in answer
    assert "[política 5.1" not in answer and "10/01/2026" not in answer
    assert observed_tools == ["get_my_order", "search_store_policies"]
    assert policy.queries == [historical["prompt"]]
    assert requests == 4  # Correction plus the missing tool stays within five requests.


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


def test_citation_retry_feedback_preserves_current_order_facts(
    tmp_path: Path,
    operational_database: Path,
    demo_customer: dict[str, int],
) -> None:
    policy = SourcePolicySearch({"4.1"})
    observed_tools: list[str] = []
    retry_feedback: list[str] = []
    requests = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal requests
        requests += 1
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            observed_tools.append("get_my_order")
            return ModelResponse(parts=[ToolCallPart("get_my_order", {"order_id": 4})])
        if len(returns) == 1:
            observed_tools.append("search_store_policies")
            return ModelResponse(parts=[ToolCallPart("search_store_policies", {})])

        order_result = cast(
            dict[str, object],
            next(part.content for part in returns if part.tool_name == "get_my_order"),
        )
        order = cast(dict[str, object], order_result["order"])
        assert order["status"] == "delivered"

        has_prior_answer = any(
            isinstance(part, TextPart) for message in messages for part in message.parts
        )
        if not has_prior_answer:
            # Preserve the operational fact but trigger citation correction.
            return ModelResponse(
                parts=[
                    TextPart(
                        "O pedido 4 consta como entregue na fotografia. Para compras "
                        "online, o prazo é de sete dias do recebimento e exige "
                        "embalagem original e ausência de sinais de uso "
                        "[política 4.1, p. 99]."
                    )
                ]
            )

        feedback = messages[-1].parts[-1]
        feedback_text = str(getattr(feedback, "content", ""))
        retry_feedback.append(feedback_text)
        if "Preserve" in feedback_text:
            corrected = (
                "O pedido 4 consta como entregue na fotografia. Para compras online, "
                "a devolução pode ser solicitada em até sete dias corridos após o "
                "recebimento, com embalagem original e sem sinais de uso "
                "[política 4.1, p. 4]. Qual foi o canal da compra e a data de "
                "recebimento?"
            )
        else:
            corrected = (
                "Para compras online, a devolução pode ser solicitada em até sete "
                "dias corridos após o recebimento, com embalagem original e sem "
                "sinais de uso [política 4.1, p. 4]. Qual foi o canal da compra e "
                "a data de recebimento?"
            )
        return ModelResponse(parts=[TextPart(corrected)])

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
    # This is a scripted pipeline regression, not a production wording validator.
    assert "O pedido 4 consta como entregue na fotografia." in answer
    assert "[política 4.1, p. 4]" in answer
    assert "fotografia importada" in answer
    assert observed_tools == ["get_my_order", "search_store_policies"]
    assert len(retry_feedback) == 1
    assert "Preserve" in retry_feedback[0]
    assert "entregue" not in retry_feedback[0].lower()
    assert requests == 4


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


def test_policy_guidance_preserves_source_conditions_without_rewriting_records() -> (
    None
):
    search = SourcePolicySearch({"2", "4.1", "5.1", "8.1", "8.2", "8.3"})
    original = json.dumps(search.records, ensure_ascii=False)
    result = PolicyTools(search).search_store_policies(
        RunContext(
            deps=ExecutionContext(),
            model=TestModel(),
            usage=RunUsage(),
            prompt="Pedido no limite e empréstimo?",
        )
    )
    notes = " ".join(result["answer_guidance"])
    # These qualifications come from the reviewed source, not nearest-neighbor scores.
    assert "acima de R$ 500,00" in original and "abaixo de R$ 500,00" in original
    assert "sem sinais de uso" in original
    assert "exatamente igual" in notes and "não confirme gratuidade" in notes
    assert "Relato de uso não comprova sinais de uso" in notes
    assert "sem afirmar que existe" in notes
    assert "não omita o fechamento" in notes
    assert json.dumps(result["records"], ensure_ascii=False) == original
