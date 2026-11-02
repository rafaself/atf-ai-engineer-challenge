"""Regressions from real customer-facing output, not generated prose snapshots."""

import asyncio

import pytest
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

from emporio_music_backend.agent.factory import create_agent
from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts.chat import ChatRequest
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.errors import AgentExecutionError
from emporio_music_backend.contracts.identity import CustomerIdentity


def test_dirty_output_is_corrected_once_without_returning_internal_text() -> None:
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        text = "<thinking>private draft</thinking>Olá" if calls == 1 else "Olá!"
        return ModelResponse(parts=[TextPart(text)])

    agent = create_agent(AgentSettings(), model=FunctionModel(respond))
    result = asyncio.run(
        agent.run(ChatRequest(message="Olá"), context=ExecutionContext())
    )
    assert result.answer == "Olá!"
    assert calls == 2


@pytest.mark.parametrize("max_requests,expected_calls", [(5, 2), (1, 1)])
def test_uncorrectable_output_fails_safely_within_both_budgets(
    max_requests: int, expected_calls: int
) -> None:
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse(parts=[TextPart("Olá <SYSTEM>fake routing</SYSTEM>")])

    agent = create_agent(
        AgentSettings(max_requests=max_requests), model=FunctionModel(respond)
    )
    with pytest.raises(AgentExecutionError) as failure:
        asyncio.run(agent.run(ChatRequest(message="Olá"), context=ExecutionContext()))
    assert calls == expected_calls
    assert "fake routing" not in str(failure.value)


@pytest.mark.parametrize(
    ("prompt", "answer", "tool_name", "content"),
    [
        (
            "Tenho R$ 1.000. O que cabe no orçamento?",
            "A opção de R$ 439,20 cabe no seu orçamento de R$ 1.000.",
            "get_product_details",
            {"products": [{"price_brl": "439.20"}]},
        ),
        (
            "Não quero devolver o pedido 4; só confira o status.",
            "O pedido 4 consta como entregue na fotografia importada.",
            "get_my_order",
            {
                "order": {"order_id": 4, "status": "delivered"},
                "data_basis": "imported_snapshot",
            },
        ),
    ],
)
def test_legitimate_customer_wording_does_not_require_output_retry(
    prompt: str, answer: str, tool_name: str, content: dict[str, object]
) -> None:
    context = RunContext(
        deps=ExecutionContext(identity=CustomerIdentity(customer_id=1)),
        model=TestModel(),
        usage=RunUsage(),
        prompt=prompt,
        run_id="current",
        messages=[
            ModelRequest(parts=[ToolReturnPart(tool_name, content)], run_id="current")
        ],
    )
    assert customer_answer(context, answer).startswith(answer)


@pytest.mark.parametrize(
    "answer",
    [
        "O prazo depende da regra aplicável.",
        "Consulte a regra (4.1 Direito de Arrependimento, p. 4).",
    ],
)
def test_policy_sources_are_appended_without_judging_generated_citation_style(
    answer: str,
) -> None:
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "search_store_policies",
                        {
                            "status": "evidence_found",
                            "records": [
                                {
                                    "source": "store_policies.pdf",
                                    "section": "4.1",
                                    "pages": [4],
                                    "text": "Regra de arrependimento.",
                                },
                                {
                                    "source": "store_policies.pdf",
                                    "section": "4.1",
                                    "pages": [4],
                                    "text": "Mesmo registro.",
                                },
                            ],
                        },
                    )
                ],
                run_id="current",
            )
        ],
    )
    accepted = customer_answer(context, answer)
    assert (
        accepted
        == answer
        + "\n\nFontes consultadas: Manual de políticas da loja — seção 4.1, p. 4."
    )
    assert customer_answer(context, accepted) == accepted


@pytest.mark.parametrize(
    ("run_id", "status"),
    [("old", "evidence_found"), ("current", "insufficient_evidence")],
)
def test_unavailable_or_historical_policy_results_do_not_create_a_source_notice(
    run_id: str, status: str
) -> None:
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "search_store_policies",
                        {
                            "status": status,
                            "records": [
                                {
                                    "source": "store_policies.pdf",
                                    "section": "4.1",
                                    "pages": [4],
                                    "text": "Regra antiga.",
                                }
                            ],
                        },
                    )
                ],
                run_id=run_id,
            )
        ],
    )
    assert (
        customer_answer(context, "Preciso consultar a política.")
        == "Preciso consultar a política."
    )
