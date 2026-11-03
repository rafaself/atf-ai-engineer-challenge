"""US-17 trace regressions: scripted models verify contracts, not LLM quality."""

from pathlib import Path

import pytest
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.output import customer_answer
from emporio_music.agent.settings import AgentSettings
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.policies import PolicyExcerpt, PolicySearchResult
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music.paths import DATA_DIRECTORY
from emporio_music.policies.corpus import PolicyCorpus
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from tests._support import run_async


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

    def search(
        self, query: str, *, policy_scope: str = "general"
    ) -> PolicySearchResult:
        self.queries.append(query)
        return {"status": "evidence_found", "records": self.records}


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
    answer = run_async(customer_answer(context, "Aqui estão os pedidos encontrados."))
    assert "fotografia importada" not in answer


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
    assert run_async(customer_answer(context, answer)) == answer


@pytest.mark.parametrize("identity", [None, CustomerIdentity(customer_id=1)])
def test_order_return_without_id_allows_clarification(
    identity: CustomerIdentity | None,
    operational_database: Path,
) -> None:
    async def clarify(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
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
    result = run_async(
        agent.run(
            ChatRequest(message="Quero devolver meu pedido."),
            context=ExecutionContext(identity=identity),
        )
    )
    assert result.answer == "Qual é o número do pedido?"
