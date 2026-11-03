"""Regressions from real customer-facing output, not generated prose snapshots."""

import asyncio

import pytest
from emporio_music.agent.factory import create_agent
from emporio_music.agent.output import customer_answer
from emporio_music.agent.settings import AgentSettings
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.errors import AgentExecutionError
from emporio_music.domain.identity import CustomerIdentity
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


def test_dirty_output_is_corrected_once_without_returning_internal_text() -> None:
    calls = 0

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
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

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
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
            "find_product_by_name",
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
    assert run_async(customer_answer(context, answer)).startswith(answer)


@pytest.mark.parametrize(
    "tool_name", ["search_available_products", "find_product_by_name"]
)
def test_operational_results_do_not_repeat_demo_disclosure(tool_name: str) -> None:
    answer = "Este produto está disponível no catálogo."
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        tool_name,
                        {
                            "products": [{"product_id": 1, "available": True}],
                            "inventory_basis": "imported_snapshot",
                        },
                    )
                ],
                run_id="current",
            )
        ],
    )

    assert run_async(customer_answer(context, answer)) == answer


@pytest.mark.parametrize(
    ("run_id", "products", "inventory_basis"),
    [
        ("old", [{"product_id": 1}], "imported_snapshot"),
        ("current", [], "imported_snapshot"),
        ("current", [{"product_id": 1}], "live"),
    ],
)
@pytest.mark.parametrize(
    "tool_name", ["search_available_products", "find_product_by_name"]
)
def test_inventory_notice_requires_current_nonempty_snapshot_results(
    run_id: str,
    products: list[dict[str, object]],
    inventory_basis: str,
    tool_name: str,
) -> None:
    answer = "Consultei o catálogo."
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        tool_name,
                        {
                            "products": products,
                            "inventory_basis": inventory_basis,
                        },
                    )
                ],
                run_id=run_id,
            )
        ],
    )

    assert run_async(customer_answer(context, answer)) == answer


def test_multiple_operational_results_do_not_add_disclosures() -> None:
    answer = "O produto está disponível."
    result = {
        "products": [{"product_id": 1, "available": True}],
        "inventory_basis": "imported_snapshot",
    }
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart("search_available_products", result),
                    ToolReturnPart("find_product_by_name", result),
                ],
                run_id="current",
            )
        ],
    )

    accepted = run_async(customer_answer(context, answer))

    assert accepted == answer
    assert run_async(customer_answer(context, accepted)) == accepted


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
    accepted = run_async(customer_answer(context, answer))
    assert (
        accepted
        == answer
        + "\n\nFontes consultadas: Manual de políticas da loja — seção 4.1, p. 4."
    )
    assert run_async(customer_answer(context, accepted)) == accepted


def test_policy_source_without_pdf_page_is_cited_separately() -> None:
    answer = "Para pedidos de R$ 500,00, o frete é grátis."
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
                                    "section": "5.1",
                                    "pages": [4],
                                    "text": "Regra original, sem igualdade.",
                                },
                                {
                                    "source": "policies/freight-clarification.json",
                                    "section": "5.1 (clarificação aprovada)",
                                    "pages": [],
                                    "text": "Clarificação aprovada da igualdade.",
                                },
                            ],
                        },
                    )
                ],
                run_id="current",
            )
        ],
    )

    accepted = run_async(customer_answer(context, answer))

    assert accepted == (
        answer + "\n\nFontes consultadas: policies/freight-clarification.json — "
        "seção 5.1 (clarificação aprovada), sem página física; "
        "Manual de políticas da loja — seção 5.1, p. 4."
    )


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
        run_async(customer_answer(context, "Preciso consultar a política."))
        == "Preciso consultar a política."
    )
