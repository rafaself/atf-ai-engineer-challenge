"""Issue #85 quote, comparison and qualified deadline behavior."""

import asyncio
import csv
import json
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import pytest
from emporio_music.agent.amounts import BRLAmount
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.quotes import ProductQuoteTools
from emporio_music.agent.settings import AgentSettings
from emporio_music.application.comparisons import compare_products
from emporio_music.application.deadlines import calculate_deadline
from emporio_music.application.quotes import (
    calculate_installment_options,
    calculate_quote,
)
from emporio_music.domain.catalog import (
    ProductBatchLookupQuery,
    ProductSearchQuery,
)
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.comparisons import ProductComparisonRequest
from emporio_music.domain.conversations import (
    ConversationMessage,
    ConversationSession,
    ExecutionContext,
)
from emporio_music.domain.deadlines import DeadlineRequest
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.orders import OrderLookupQuery
from emporio_music.domain.quotes import (
    QuoteItemInput,
    QuotePaymentIntent,
    QuoteRequest,
    ShippingDestination,
)
from emporio_music.infrastructure.catalog_import import (
    CATEGORY_COLUMNS,
    PRODUCT_COLUMNS,
    PROMOTION_COLUMNS,
    import_catalog,
)
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.infrastructure.sqlite_repository import SQLiteProductRepository
from pydantic import Field, ValidationError
from pydantic_ai import RunContext
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


def _catalog(tmp_path: Path) -> Path:
    categories = tmp_path / "categories.csv"
    products = tmp_path / "products.csv"
    promotions = tmp_path / "promotions.csv"
    database = tmp_path / "catalog.sqlite3"
    with categories.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CATEGORY_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {"category_id": "1", "name": "Instrumentos", "description": "Teste"}
        )
    prices = {
        1: 50_000,
        2: 49_999,
        3: 50_100,
        4: 200_000,
        5: 201_000,
        6: 200_001,
        7: 10_000,
        8: 4_999,
        9: 31_999,
        10: 32_000,
        11: 70_000,
        12: 119_999,
        13: 120_000,
        14: 50_000,
        15: 50_000,
    }
    with products.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PRODUCT_COLUMNS)
        writer.writeheader()
        for product_id, cents in prices.items():
            writer.writerow(
                {
                    "product_id": product_id,
                    "category_id": 1,
                    "name": f"Instrument {product_id}",
                    "description": "Quote fixture",
                    "price_brl": f"{cents // 100}.{cents % 100:02d}",
                    "stock_quantity": 3 if product_id == 14 else 2,
                    "status": "active",
                    "specs": json.dumps({}),
                    "created_at": "2026-01-01",
                }
            )
    with promotions.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=PROMOTION_COLUMNS)
        writer.writeheader()
        writer.writerows(
            [
                {
                    "promotion_id": "1",
                    "product_id": "3",
                    "discount_percent": "1",
                    "description": "Threshold fixture",
                    "is_active": "1",
                },
                {
                    "promotion_id": "2",
                    "product_id": "5",
                    "discount_percent": "1",
                    "description": "Split threshold fixture",
                    "is_active": "1",
                },
                {
                    "promotion_id": "3",
                    "product_id": "7",
                    "discount_percent": "50",
                    "description": "Inactive fixture",
                    "is_active": "0",
                },
                {
                    "promotion_id": "4",
                    "product_id": "15",
                    "discount_percent": "100",
                    "description": "Zero-total fixture",
                    "is_active": "1",
                },
            ]
        )
    import_catalog(products, categories, promotions, database)
    return database


def _quote(
    repository: SQLiteProductRepository,
    product_ids: tuple[int, ...],
    intent: QuotePaymentIntent,
    *,
    quantities: tuple[int, ...] | None = None,
    pix_amount: int | None = None,
    destination: ShippingDestination | None = None,
) -> Any:
    quantities = quantities or (1,) * len(product_ids)
    request = QuoteRequest(
        items=tuple(
            QuoteItemInput(product_id=product_id, quantity=quantity)
            for product_id, quantity in zip(product_ids, quantities, strict=True)
        ),
        payment_intent=intent,
        pix_allocation_centavos=pix_amount,
        destination=destination,
    )
    lookup = repository.lookup_many(
        ProductBatchLookupQuery(product_ids=product_ids, payment_method="standard")
    )
    return calculate_quote(request, lookup)


def test_multi_product_quote_uses_one_real_sqlite_snapshot_and_nonstacking_pricing(
    operational_database: Path,
) -> None:
    repository = SQLiteProductRepository(
        operational_database.parent / "operational-catalog.sqlite3"
    )
    request = QuoteRequest(
        items=(
            QuoteItemInput(product_id=127, quantity=2),
            QuoteItemInput(product_id=108, quantity=1),
        ),
        payment_intent="compare",
    )
    lookup = repository.lookup_many(
        ProductBatchLookupQuery(
            product_ids=(127, 108, 999_999), payment_method="standard"
        )
    )
    assert lookup.requested_product_ids == (127, 108, 999_999)
    assert [product.product_id for product in lookup.products] == [127, 108]
    assert lookup.missing_product_ids == (999_999,)

    complete = repository.lookup_many(
        ProductBatchLookupQuery(product_ids=(127, 108), payment_method="standard")
    )
    result = calculate_quote(request, complete)
    assert result.calculation_status == "complete"
    assert result.original_total_centavos == 1_271_800
    assert result.standard_total_centavos == 1_264_620
    assert result.pix_total_centavos == 1_204_620
    assert result.selected_installment_options
    assert (
        result.selected_installment_options[0].total_centavos
        == result.standard_total_centavos
    )
    assert result.installment_total_scope == "merchandise_only"
    promo, regular = result.lines
    assert promo.standard_subtotal_centavos == 64_620
    assert promo.pix_subtotal_centavos == 64_620
    assert promo.standard_pricing is not None
    assert promo.standard_pricing.discount_kind == "promotion"
    assert promo.standard_subtotal_brl == "646.20"
    assert regular.standard_subtotal_centavos == 1_200_000
    assert regular.pix_subtotal_centavos == 1_140_000
    assert result.standard_total_brl == "12646.20"
    assert result.max_installments == 12

    pix = calculate_quote(
        QuoteRequest(items=request.items, payment_intent="pix"),
        complete,
    )
    assert pix.selected_merchandise_total_centavos == 1_204_620
    assert pix.selected_installment_options == ()

    credit = calculate_quote(
        QuoteRequest(
            items=request.items,
            payment_intent="credit",
        ),
        complete,
    )
    assert credit.max_installments == 12
    twelve = next(
        option for option in credit.selected_installment_options if option.count == 12
    )
    assert twelve.total_brl == "12646.20"
    assert len(twelve.amounts_brl) == 12


def test_installment_options_use_confirmed_ranges_and_centavo_exact_allocations() -> (
    None
):
    assert calculate_installment_options(0) == ()
    assert calculate_installment_options(4_999) == ()
    assert [plan.count for plan in calculate_installment_options(5_000)] == [1, 2, 3]
    assert 4 not in {plan.count for plan in calculate_installment_options(31_999)}
    four_at_minimum = calculate_installment_options(32_000)
    assert next(
        plan for plan in four_at_minimum if plan.count == 4
    ).amounts_centavos == (
        8_000,
        8_000,
        8_000,
        8_000,
    )
    assert 7 not in {plan.count for plan in calculate_installment_options(69_999)}
    seven_at_minimum = calculate_installment_options(70_000)
    assert next(
        plan for plan in seven_at_minimum if plan.count == 7
    ).amounts_centavos == (
        10_000,
        10_000,
        10_000,
        10_000,
        10_000,
        10_000,
        10_000,
    )
    eleven = calculate_installment_options(119_999)
    twelve = calculate_installment_options(120_000)
    assert max(plan.count for plan in eleven) == 11
    assert max(plan.count for plan in twelve) == 12
    three = next(
        plan for plan in calculate_installment_options(100_001) if plan.count == 3
    )
    assert three.amounts_centavos == (33_334, 33_334, 33_333)
    assert three.amounts_brl == ("333.34", "333.34", "333.33")
    assert sum(three.amounts_centavos) == 100_001


def test_installment_policy_conflicts_are_reported_as_uncertain(
    tmp_path: Path,
) -> None:
    repository = SQLiteProductRepository(_catalog(tmp_path))
    result = _quote(repository, (10,), "credit", quantities=(1,))

    four = next(
        option for option in result.selected_installment_options if option.count == 4
    )
    assert four.eligibility == "policy_ambiguous"
    assert result.max_installments == 3
    assert result.uncertain_max_installments == 4

    requested = calculate_quote(
        QuoteRequest(
            items=(QuoteItemInput(product_id=10, quantity=1),),
            payment_intent="credit",
            requested_installments=4,
        ),
        repository.lookup_many(
            ProductBatchLookupQuery(product_ids=(10,), payment_method="standard")
        ),
    )
    assert requested.requested_installment_status == "policy_ambiguous"


def test_zero_value_promotion_produces_quote_without_installments(
    tmp_path: Path,
) -> None:
    repository = SQLiteProductRepository(_catalog(tmp_path))
    result = _quote(repository, (15,), "credit")

    assert result.standard_total_centavos == 0
    assert result.quoted_total_centavos == 0
    assert result.selected_installment_options == ()
    assert result.max_installments is None
    assert result.uncertain_max_installments is None


def test_freight_and_mixed_payment_boundaries_preserve_unresolved_basis(
    tmp_path: Path,
) -> None:
    repository = SQLiteProductRepository(_catalog(tmp_path))

    exactly_500 = _quote(repository, (1,), "credit", destination="campo_grande_metro")
    assert exactly_500.shipping.status == "supported"
    assert exactly_500.shipping.charge_centavos == 0
    assert exactly_500.shipping.charge_brl == "0.00"
    assert exactly_500.quoted_total_centavos == 50_000
    assert exactly_500.quoted_total_brl == "500.00"
    assert exactly_500.quoted_total_scope == "includes_supported_shipping"
    below_500 = _quote(repository, (2,), "credit", destination="campo_grande_metro")
    assert below_500.shipping.charge_centavos == 3_500
    assert below_500.quoted_total_centavos == 53_499
    crossed_freight_threshold = _quote(
        repository, (3,), "credit", destination="campo_grande_metro"
    )
    assert crossed_freight_threshold.shipping.status == "basis_ambiguous"
    assert crossed_freight_threshold.quoted_total_centavos is None
    assert crossed_freight_threshold.selected_installment_options
    assert crossed_freight_threshold.installment_total_scope == "merchandise_only"

    exact_2_000 = _quote(repository, (4,), "split", pix_amount=100_000)
    assert exact_2_000.split_payment.status == "not_eligible_at_threshold"
    above_2_000 = _quote(repository, (6,), "split", pix_amount=100_000)
    assert above_2_000.split_payment.status == "eligible"
    assert above_2_000.split_payment.credit_amount_centavos == 100_001
    assert above_2_000.split_payment.credit_amount_brl == "1000.01"
    assert above_2_000.split_payment.pix_amount_brl == "1000.00"
    assert above_2_000.split_payment.pix_discount_applied == "policy_ambiguous"
    assert above_2_000.max_installments == 10
    assert above_2_000.uncertain_max_installments is None
    split_with_conflicting_minimum = _quote(
        repository, (6,), "split", pix_amount=150_001
    )
    assert split_with_conflicting_minimum.split_payment.credit_amount_centavos == 50_000
    assert split_with_conflicting_minimum.max_installments == 5
    assert split_with_conflicting_minimum.uncertain_max_installments == 6
    crossed_split_threshold = _quote(repository, (5,), "split", pix_amount=100_000)
    assert crossed_split_threshold.split_payment.status == "eligibility_basis_ambiguous"

    inactive_offer = _quote(repository, (7,), "compare")
    assert inactive_offer.standard_total_centavos == 10_000
    assert inactive_offer.pix_total_centavos == 9_500
    unsupported = _quote(repository, (1,), "credit", destination="other_city")
    assert unsupported.shipping.status == "unsupported_destination"
    assert unsupported.shipping.charge_centavos is None
    assert unsupported.quoted_total_centavos is None
    assert unsupported.selected_installment_options
    assert unsupported.selected_installment_options[0].total_centavos == 50_000
    assert unsupported.installment_total_scope == "merchandise_only"


def test_quote_does_not_return_a_total_for_missing_unavailable_or_insufficient_items(
    tmp_path: Path,
) -> None:
    repository = SQLiteProductRepository(_catalog(tmp_path))
    missing = _quote(repository, (999_999,), "credit")
    assert missing.calculation_status == "missing_products"
    assert missing.selected_merchandise_total_centavos is None
    unavailable_request = QuoteRequest(
        items=(QuoteItemInput(product_id=14, quantity=4),), payment_intent="credit"
    )
    unavailable_lookup = repository.lookup_many(
        ProductBatchLookupQuery(product_ids=(14,), payment_method="standard")
    )
    unavailable = calculate_quote(unavailable_request, unavailable_lookup)
    assert unavailable.calculation_status == "unavailable_products"
    assert unavailable.insufficient_stock == ((14, 4, 3),)
    assert unavailable.selected_merchandise_total_centavos is None
    with pytest.raises(ValidationError):
        QuoteRequest(
            items=(QuoteItemInput(product_id=1, quantity=1),) * 2,
            payment_intent="credit",
        )


def test_comparison_returns_ties_extrema_and_differences_from_sqlite(
    tmp_path: Path,
) -> None:
    repository = SQLiteProductRepository(_catalog(tmp_path))
    request = ProductComparisonRequest(
        product_ids=(1, 2, 14),
        fields=("original_price", "payable_price", "stock_quantity"),
        payment_method="standard",
    )
    result = compare_products(
        request,
        repository.lookup_many(
            ProductBatchLookupQuery(
                product_ids=request.product_ids, payment_method="standard"
            )
        ),
    )
    assert result.status == "complete"
    original, payable, stock = result.comparisons
    assert original.minimum_product_ids == (2,)
    assert original.maximum_product_ids == (1, 14)
    assert original.difference == 1
    assert original.difference_brl == "0.01"
    assert payable.maximum_product_ids == (1, 14)
    assert stock.minimum_product_ids == (1, 2)
    assert stock.maximum_product_ids == (14,)
    assert stock.difference_brl is None
    missing = compare_products(
        ProductComparisonRequest(
            product_ids=(1, 999_999),
            fields=("stock_quantity",),
            payment_method="standard",
        ),
        repository.lookup_many(
            ProductBatchLookupQuery(product_ids=(1, 999_999), payment_method="standard")
        ),
    )
    assert missing.status == "missing_products"
    assert missing.comparisons == ()


def test_deadlines_use_correct_event_and_qualify_missing_receipt_and_holidays(
    operational_database: Path,
) -> None:
    orders = SQLiteOrderRepository(operational_database)
    owner = CustomerIdentity(customer_id=3)
    order = orders.get_order(owner, OrderLookupQuery(order_id=1))
    assert order is not None

    delivery = calculate_deadline(
        DeadlineRequest(deadline_type="delivery", order_id=1),
        order=order,
        order_requested=True,
    )
    assert delivery.status == "estimated"
    assert delivery.deadline_start_date == date(2025, 10, 25)
    assert "does not confirm" in delivery.note

    return_without_receipt = calculate_deadline(
        DeadlineRequest(deadline_type="online_return", order_id=1),
        order=order,
        order_requested=True,
    )
    assert return_without_receipt.status == "missing_reference_date"
    assert return_without_receipt.deadline_end_date is None
    return_with_receipt = calculate_deadline(
        DeadlineRequest(
            deadline_type="online_return",
            order_id=1,
            reference_date=date(2025, 10, 26),
            reference_event="actual_receipt",
            request_date=date(2025, 11, 2),
        ),
        order=order,
        order_requested=True,
    )
    assert return_with_receipt.deadline_end_date == date(2025, 11, 2)
    assert return_with_receipt.request_status == "within_window"
    assert return_with_receipt.actual_receipt_date_source == "customer_reported"

    exchange = calculate_deadline(
        DeadlineRequest(
            deadline_type="defect_exchange",
            order_id=1,
            request_date=date(2025, 11, 14),
        ),
        order=order,
        order_requested=True,
    )
    assert exchange.deadline_start_date == date(2025, 10, 15)
    assert exchange.deadline_end_date == date(2025, 11, 14)
    assert exchange.request_status == "within_window"

    warranty = calculate_deadline(
        DeadlineRequest(
            deadline_type="warranty",
            order_id=1,
            reference_date=date(2025, 10, 25),
            reference_event="actual_receipt",
            request_date=date(2026, 1, 23),
        ),
        order=order,
        order_requested=True,
    )
    assert warranty.deadline_start_date == date(2025, 10, 25)
    assert warranty.deadline_end_date == date(2026, 1, 23)
    assert warranty.request_status == "within_window"
    assert warranty.actual_receipt_date_source == "customer_reported"

    business_days = calculate_deadline(
        DeadlineRequest(
            deadline_type="delivery",
            reference_date=date(2026, 1, 2),
            reference_event="dispatch",
            destination="campo_grande_metro",
        )
    )
    assert business_days.deadline_start_date == date(2026, 1, 5)
    assert business_days.deadline_end_date == date(2026, 1, 7)
    assert business_days.calendar_basis == "weekends_only_holidays_unmodeled"
    assert "conditional" in business_days.note
    assert (
        "does not explicitly establish dispatch as the start event"
        in business_days.note
    )

    refund = calculate_deadline(
        DeadlineRequest(deadline_type="refund", order_id=1),
        order=order,
        order_requested=True,
    )
    assert refund.status == "policy_reference_unspecified"
    assert refund.duration_max_days == 10
    assert refund.deadline_end_date is None


def test_deadline_requires_delivery_service_and_preserves_customer_scope(
    operational_database: Path,
) -> None:
    repo = SQLiteOrderRepository(operational_database)
    unknown_order = repo.get_order(
        CustomerIdentity(customer_id=1), OrderLookupQuery(order_id=1)
    )
    assert unknown_order is None
    hidden = calculate_deadline(
        DeadlineRequest(deadline_type="delivery", order_id=1),
        order=unknown_order,
        order_requested=True,
    )
    assert hidden.status == "order_not_found"

    no_dispatch = calculate_deadline(DeadlineRequest(deadline_type="delivery"))
    assert no_dispatch.status == "missing_reference_date"
    no_service = calculate_deadline(
        DeadlineRequest(
            deadline_type="delivery",
            reference_date=date(2026, 1, 2),
            reference_event="dispatch",
            destination="other_city",
        )
    )
    assert no_service.status == "missing_service"
    national = calculate_deadline(
        DeadlineRequest(
            deadline_type="delivery",
            reference_date=date(2026, 1, 2),
            reference_event="dispatch",
            destination="other_city",
            delivery_service="pac",
        )
    )
    assert national.deadline_start_date == date(2026, 1, 9)
    assert national.deadline_end_date == date(2026, 1, 20)
    assert national.status == "estimated"
    assert national.calendar_basis == "weekends_only_holidays_unmodeled"

    selection = calculate_deadline(
        DeadlineRequest(deadline_type="online_return", order_id=1),
        order_requested=True,
        customer_selection_required=True,
    )
    assert selection.status == "customer_selection_required"

    with pytest.raises(ValidationError):
        DeadlineRequest(
            deadline_type="online_return",
            reference_date=date(2026, 1, 2),
            reference_event="purchase",
        )


@pytest.mark.parametrize(
    ("service", "minimum_days", "maximum_days"),
    [("pac", 5, 12), ("sedex", 2, 5), ("jadlog", 3, 8)],
)
def test_national_delivery_deadline_uses_each_published_service_range(
    service: Literal["pac", "sedex", "jadlog"],
    minimum_days: int,
    maximum_days: int,
) -> None:
    result = calculate_deadline(
        DeadlineRequest(
            deadline_type="delivery",
            reference_date=date(2026, 1, 5),
            reference_event="dispatch",
            destination="other_city",
            delivery_service=service,
        )
    )
    assert result.duration_min_days == minimum_days
    assert result.duration_max_days == maximum_days
    assert result.deadline_start_date is not None
    assert result.deadline_end_date is not None
    assert result.deadline_start_date.weekday() < 5
    assert result.deadline_end_date.weekday() < 5


def test_multi_turn_agent_corrects_old_installment_claim_with_current_quote(
    operational_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import emporio_music.agent.factory as agent_factory

    async def accept_controlled_answer(
        context: RunContext[ExecutionContext], answer: str
    ) -> str:
        return answer

    monkeypatch.setattr(agent_factory, "customer_answer", accept_controlled_answer)
    production_quote = ProductQuoteTools.calculate_quote

    async def calculate_quote(
        self: ProductQuoteTools,
        items: Annotated[list[QuoteItemInput], Field(min_length=1, max_length=10)],
        payment_intent: QuotePaymentIntent,
        requested_installments: Annotated[int, Field(strict=True, ge=1, le=12)]
        | None = None,
        pix_amount_brl: BRLAmount | None = None,
        destination: ShippingDestination | None = None,
    ) -> dict[str, object]:
        return production_quote(
            self,
            items,
            payment_intent,
            requested_installments,
            pix_amount_brl,
            destination,
        )

    monkeypatch.setattr(ProductQuoteTools, "calculate_quote", calculate_quote)

    catalog = SQLiteProductRepository(
        operational_database.parent / "operational-catalog.sqlite3"
    )
    product = catalog.search(
        ProductSearchQuery(
            product_name="Takamine GD20",
            available_only=False,
            limit=1,
            payment_method="standard",
        )
    ).products[0]
    orders = SQLiteOrderRepository(operational_database)
    session = ConversationSession(owner=CustomerIdentity(customer_id=1))
    observed_quotes: list[dict[str, Any]] = []

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool_returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if tool_returns:
            quote = cast(dict[str, Any], tool_returns[-1].content)
            observed_quotes.append(quote)
            assert quote["quoted_total_brl"] == "2199.00"
            return ModelResponse(
                parts=[
                    TextPart(
                        f"Correção: a cotação atual permite até {quote['max_installments']} parcelas."
                    )
                ]
            )
        latest_user = next(
            part.content
            for message in reversed(messages)
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        if not isinstance(latest_user, str):
            raise AssertionError("Expected a text user message")
        if latest_user.startswith("Qual é o limite"):
            return ModelResponse(parts=[TextPart("O máximo é 10 parcelas.")])
        tool_names = {tool.name for tool in info.function_tools}
        assert {
            "calculate_quote",
            "compare_products",
            "calculate_deadline",
        } <= tool_names
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "calculate_quote",
                    {
                        "items": [{"product_id": product.product_id, "quantity": 1}],
                        "payment_intent": "credit",
                    },
                )
            ]
        )

    from emporio_music.domain.policies import PolicySearchResult

    class UnusedPolicies:
        def search(
            self, query: str, *, policy_scope: str = "general"
        ) -> PolicySearchResult:
            raise AssertionError("This scenario only asks about installments")

    agent = create_store_agent(
        AgentSettings(),
        catalog,
        orders,
        model=FunctionModel(respond),
        policy_search=UnusedPolicies(),
    )
    identity = session.owner
    first_message = "Qual é o limite de parcelas para o Takamine GD20?"
    first = asyncio.run(
        agent.run(
            ChatRequest(message=first_message),
            context=ExecutionContext(identity=identity, session=session),
        )
    )
    assert first.answer == "O máximo é 10 parcelas."
    second = asyncio.run(
        agent.run(
            ChatRequest(
                message="Você disse no turno anterior que eram 10. Confirme com a cotação atual."
            ),
            context=ExecutionContext(
                identity=identity,
                session=session,
                history=(
                    ConversationMessage(role="user", content=first_message),
                    ConversationMessage(role="assistant", content=first.answer),
                ),
            ),
        )
    )
    assert observed_quotes[0]["max_installments"] == 12
    assert second.answer == "Correção: a cotação atual permite até 12 parcelas."
