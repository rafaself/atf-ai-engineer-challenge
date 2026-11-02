"""Regressions from real customer-facing output, not generated prose snapshots."""

import asyncio

import pytest
from pydantic_ai import ModelRetry, RunContext, Tool
from pydantic_ai.messages import (
    ModelMessage,
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

from emporio_music_backend.agent.factory import create_agent
from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts.chat import ChatRequest
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.errors import AgentExecutionError


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


@pytest.mark.parametrize("correct_on_retry", [True, False])
def test_unsupported_price_retries_once_then_returns_a_quote_or_fails(
    correct_on_retry: bool,
) -> None:
    def get_product_details(product_name: str) -> dict[str, object]:
        return {
            "products": [
                {
                    "price_brl": "549.00",
                    "pricing": {
                        "final_price_brl": "439.20",
                        "discount_kind": "promotion",
                    },
                }
            ]
        }

    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        if not any(
            isinstance(part, ToolReturnPart)
            for message in messages
            for part in message.parts
        ):
            return ModelResponse(
                parts=[ToolCallPart("get_product_details", {"product_name": "Ohana"})]
            )
        price = "439,20" if correct_on_retry and calls == 3 else "405,28"
        return ModelResponse(parts=[TextPart(f"Preço final: R$ {price}.")])

    agent = create_agent(
        AgentSettings(),
        model=FunctionModel(respond),
        tools=[Tool(get_product_details)],
    )
    if correct_on_retry:
        result = asyncio.run(
            agent.run(
                ChatRequest(message="Tenho R$ 1.000. E no PIX?"),
                context=ExecutionContext(),
            )
        )
        assert result.answer.count("439,20") == 1
        assert "405,28" not in result.answer
    else:
        with pytest.raises(AgentExecutionError):
            asyncio.run(
                agent.run(
                    ChatRequest(message="Tenho R$ 1.000. E no PIX?"),
                    context=ExecutionContext(),
                )
            )
    assert calls == 3


@pytest.mark.parametrize(
    "answer,accepted",
    [
        ("Preço: R$ 439,20.", True),
        ("Preço: R$ 439.20.", True),
        ("No seu orçamento: opção por R$ 439,20; pedido de R$ 799,90.", True),
        ("Até R$ 1.000: opção por R$ 439,20.", False),
        ("Preço: R$ 1.000.", False),
        ("Preço histórico: R$ 405,28.", False),
    ],
)
def test_price_check_uses_only_current_quotes_and_totals(
    answer: str, accepted: bool
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
                        "get_product_details",
                        {"products": [{"price_brl": "405.28"}]},
                    )
                ],
                run_id="old",
            ),
            ModelResponse(
                parts=[
                    ToolCallPart("search_available_products", {"max_price_brl": 1000})
                ],
                run_id="current",
            ),
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "search_available_products",
                        {
                            "products": [
                                {
                                    "price_brl": "549.00",
                                    "pricing": {"final_price_brl": "439.20"},
                                }
                            ]
                        },
                    ),
                    ToolReturnPart("get_my_order", {"order": {"total_brl": "799.90"}}),
                ],
                run_id="current",
            ),
        ],
    )
    if accepted:
        assert customer_answer(context, answer) == answer
    else:
        with pytest.raises(ModelRetry):
            customer_answer(context, answer)


def test_price_without_current_retrieval_requires_correction() -> None:
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[],
    )
    with pytest.raises(ModelRetry):
        customer_answer(context, "O preço é R$ 405,28.")


def test_policy_amount_requires_current_evidence_and_matching_source_citation() -> None:
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
                                    "text": "Frete abaixo de R$ 500,00: taxa fixa de R$ 35,00.",
                                }
                            ],
                        },
                    )
                ],
                run_id="current",
            )
        ],
    )

    answer = (
        "A taxa fixa é R$ 35,00 para pedidos abaixo do limite [política 5.1, p. 4]."
    )
    assert customer_answer(context, answer) == answer


def test_policy_answer_requires_a_citation_from_this_turn() -> None:
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
                                    "section": "2",
                                    "pages": [2],
                                    "text": "Horário da loja.",
                                }
                            ],
                        },
                    )
                ],
                run_id="current",
            )
        ],
    )

    with pytest.raises(ModelRetry):
        customer_answer(context, "A loja atende em horário comercial.")


@pytest.mark.parametrize("evidence_run", [None, "previous", "current"])
@pytest.mark.parametrize("page", [2, 3])
def test_explicit_section_page_reference_still_requires_current_provenance(
    evidence_run: str | None,
    page: int,
) -> None:
    messages: list[ModelMessage] = []
    if evidence_run is not None:
        messages.append(
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "search_store_policies",
                        {
                            "status": "evidence_found",
                            "records": [
                                {
                                    "source": "store_policies.pdf",
                                    "section": "2",
                                    "pages": [2],
                                    "text": "Domingos e feriados: fechado.",
                                }
                            ],
                        },
                    )
                ],
                run_id=evidence_run,
            )
        )
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=messages,
    )
    answer = f"Fechada em feriados (seção 2, p. {page})."
    if evidence_run == "current" and page == 2:
        assert customer_answer(context, answer) == answer
    else:
        with pytest.raises(ModelRetry):
            customer_answer(context, answer)


@pytest.mark.parametrize("evidence_run", [None, "previous", "current"])
@pytest.mark.parametrize(
    "answer", ["Prazo de sete dias [política 4.1, p. 4].", "Prazo [política 4.1]."]
)
def test_policy_citation_cannot_create_its_own_provenance(
    evidence_run: str | None, answer: str
) -> None:
    # A current insufficient-evidence return, an old successful return and no
    # lookup at all must all reject a citation, even without a monetary claim.
    messages: list[ModelMessage] = []
    if evidence_run:
        messages.append(
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "search_store_policies",
                        {
                            "status": "insufficient_evidence"
                            if evidence_run == "current"
                            else "evidence_found",
                            "records": []
                            if evidence_run == "current"
                            else [
                                {
                                    "source": "store_policies.pdf",
                                    "section": "4.1",
                                    "pages": [4],
                                    "text": "Prazo de sete dias.",
                                }
                            ],
                        },
                    )
                ],
                run_id=evidence_run,
            )
        )
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=messages,
    )
    with pytest.raises(ModelRetry):
        customer_answer(context, answer)


def test_policy_amount_must_cite_the_section_that_contains_it() -> None:
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
                                    "text": "Frete abaixo de R$ 500,00: taxa fixa de R$ 35,00.",
                                }
                            ],
                        },
                    )
                ],
                run_id="current",
            )
        ],
    )

    with pytest.raises(ModelRetry):
        customer_answer(
            context,
            "A taxa é R$ 35,00 [política 5.2, p. 4].",
        )


def test_historical_policy_amount_does_not_authorize_current_answer() -> None:
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
                                    "text": "Taxa de frete: R$ 35,00.",
                                }
                            ],
                        },
                    )
                ],
                run_id="previous",
            )
        ],
    )

    with pytest.raises(ModelRetry):
        customer_answer(context, "A taxa é R$ 35,00 [política 5.1, p. 4].")


def test_combined_output_failures_include_current_prices_in_one_correction() -> None:
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "get_product_details",
                        {
                            "products": [
                                {
                                    "price_brl": "549.00",
                                    "pricing": {"final_price_brl": "439.20"},
                                }
                            ]
                        },
                    )
                ],
                run_id="current",
            )
        ],
    )
    with pytest.raises(ModelRetry) as correction:
        customer_answer(context, "<thinking>Rascunho</thinking>Preço: R$ 405,28.")
    assert "439.20" in str(correction.value)
    assert "549.00" in str(correction.value)
    assert "get_my_order" not in str(correction.value)
    assert "search_store_policies" not in str(correction.value)
    assert "previsão de entrega" not in str(correction.value)


@pytest.mark.parametrize("customer_history", [True, False])
def test_budget_comparison_does_not_repeat_historical_amounts(
    customer_history: bool,
) -> None:
    prior_message: ModelMessage = (
        ModelRequest(parts=[UserPromptPart("Tenho R$ 1.000.")], run_id="old")
        if customer_history
        else ModelResponse(parts=[TextPart("Preço: R$ 1.000.")], run_id="old")
    )
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            prior_message,
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "get_product_details",
                        {"products": [{"price_brl": "2199.00"}]},
                    )
                ],
                run_id="current",
            ),
        ],
    )
    answer = "O preço é R$ 2.199,00, acima do seu orçamento."
    assert customer_answer(context, answer) == answer
    with pytest.raises(ModelRetry):
        customer_answer(
            context, "O preço é R$ 2.199,00, acima do seu orçamento de R$ 1.000."
        )


@pytest.mark.parametrize("retrieved_price", [None, "2199.00"])
def test_customer_amount_cannot_authorize_a_product_price(
    retrieved_price: str | None,
) -> None:
    parts: list[UserPromptPart | ToolReturnPart] = [
        UserPromptPart("O Takamine GD20 custa R$ 1,00?")
    ]
    if retrieved_price is not None:
        parts.append(
            ToolReturnPart(
                "get_product_details",
                {"products": [{"price_brl": retrieved_price}]},
            )
        )
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[ModelRequest(parts=parts, run_id="current")],
    )
    with pytest.raises(ModelRetry):
        customer_answer(context, "O Takamine GD20 custa R$ 1,00.")


def test_malformed_customer_amount_does_not_break_a_valid_tool_quote() -> None:
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    UserPromptPart("Tenho R$ 1.000.00. Quanto custa o GD20?"),
                    ToolReturnPart(
                        "get_product_details",
                        {"products": [{"price_brl": "2199.00"}]},
                    ),
                ],
                run_id="current",
            )
        ],
    )
    assert customer_answer(context, "Preço: R$ 2.199,00.") == "Preço: R$ 2.199,00."
