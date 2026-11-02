"""US-17 trace regressions: scripted models verify contracts, not LLM quality."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
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


def test_live_mixed_answer_with_both_tools_still_requires_snapshot_disclosure() -> None:
    report = json.loads(
        (DATA_DIRECTORY.parent / "docs/examples/us-18/live-captures.json").read_text()
    )
    run = next(
        case for case in report["runs"] if case["case_id"] == "mixed-order-return"
    )
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
    with pytest.raises(ModelRetry, match="fotografia importada"):
        customer_answer(context, run["http_response"]["answer"])


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


def test_recorded_qwen_mixed_answer_retries_overstated_use_condition() -> None:
    run = json.loads(
        (
            DATA_DIRECTORY.parent / "docs/examples/us-18/mixed-rule-feedback-1.json"
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

    with pytest.raises(ModelRetry) as correction:
        customer_answer(context, answer)
    assert "sem sinais de uso" in str(correction.value)
    assert "sinais visíveis de uso" in str(correction.value)

    corrected = answer.replace(
        "O instrumento está em perfeito estado, com embalagem original, "
        "acessórios e manuais?",
        "Há sinais visíveis de uso? Você tem embalagem original, acessórios e manuais?",
    )
    assert corrected != answer
    assert customer_answer(context, corrected) == corrected
    assert "seção 4.1, p. 4" in answer
    assert "sem sinais de uso" in answer


def test_latest_qwen_answer_gets_exact_imported_snapshot_correction() -> None:
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

    with pytest.raises(ModelRetry) as correction:
        customer_answer(context, answer)
    assert "O status do pedido vem de uma fotografia importada" in str(correction.value)
    assert "confirmação ao vivo" in str(correction.value)

    corrected = answer.replace(
        'O pedido 4 está listado como "entregue" na nossa base de dados, mas a '
        "data real de recebimento não está disponível.",
        "O pedido 4 aparece como entregue na fotografia importada, sem "
        "confirmação ao vivo. A data real de recebimento não está disponível.",
    )
    assert corrected != answer
    accepted = customer_answer(context, corrected)
    assert accepted == corrected
    assert "pedido 4" in accepted
    assert "entregue" in accepted
    assert "fotografia importada" in accepted
    assert "sem confirmação ao vivo" in accepted


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
