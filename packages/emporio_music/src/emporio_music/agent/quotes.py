"""Pydantic AI wrappers for deterministic quotes and product comparisons."""

from typing import Annotated

from pydantic import Field
from pydantic_ai import Tool

from emporio_music.agent.amounts import BRLAmount, brl_to_centavos
from emporio_music.application.comparisons import (
    compare_products as calculate_comparison,
)
from emporio_music.application.quotes import calculate_quote as calculate_product_quote
from emporio_music.diagnostics import trace
from emporio_music.domain.catalog import ProductBatchLookupQuery
from emporio_music.domain.comparisons import (
    ComparisonField,
    ProductComparisonRequest,
)
from emporio_music.domain.pricing import PaymentMethod
from emporio_music.domain.quotes import (
    QuoteItemInput,
    QuotePaymentIntent,
    QuoteRequest,
    ShippingDestination,
)
from emporio_music.ports.catalog import ProductRepository


class ProductQuoteTools:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def calculate_quote(
        self,
        items: Annotated[list[QuoteItemInput], Field(min_length=1, max_length=10)],
        payment_intent: QuotePaymentIntent,
        requested_installments: Annotated[int, Field(strict=True, ge=1, le=12)]
        | None = None,
        pix_amount_brl: BRLAmount | None = None,
        destination: ShippingDestination | None = None,
    ) -> dict[str, object]:
        """Quote up to ten distinct identified products from one catalog snapshot.

        Use product IDs from a current catalog result. Standard pricing applies an
        active promotion; PIX uses the existing 5% rule only when no promotion
        applies. Compare returns both alternatives. Credit returns supported
        installment plans. Split requires an explicit PIX amount and reports the
        policy's unresolved mixed-PIX discount separately. Missing, unavailable,
        or insufficient-stock items prevent a cart total. Shipping is reported
        separately and only when its policy basis is supported.

        Args:
            items: One to ten distinct product IDs and requested quantities.
            payment_intent: compare, pix, credit, or split as explicitly requested.
            requested_installments: Requested count from 1 to 12 for credit/split.
            pix_amount_brl: The customer's requested PIX allocation in a split, reais.
            destination: Campo Grande metro or another city; other-city freight has no supported price. Split quotes cannot include shipping because tender allocation is unspecified.
        """
        request = QuoteRequest(
            items=tuple(items),
            payment_intent=payment_intent,
            requested_installments=requested_installments,
            pix_allocation_centavos=brl_to_centavos(pix_amount_brl),
            destination=destination,
        )
        trace("tool.called", tool="calculate_quote", item_count=len(items))
        lookup = self.repository.lookup_many(
            ProductBatchLookupQuery(
                product_ids=tuple(item.product_id for item in items),
                payment_method="standard",
            )
        )
        result = calculate_product_quote(request, lookup)
        trace(
            "tool.result",
            tool="calculate_quote",
            status=result.calculation_status,
            item_count=len(result.lines),
        )
        return {
            **result.model_dump(mode="json"),
            "price_basis": "computed_quote",
            "inventory_basis": "simulated_current",
        }

    def compare_products(
        self,
        product_ids: Annotated[
            list[Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]],
            Field(min_length=2, max_length=10),
        ],
        fields: Annotated[list[ComparisonField], Field(min_length=1, max_length=3)],
        payment_method: PaymentMethod,
    ) -> dict[str, object]:
        """Compare numeric fields for two to ten specifically identified products.

        Use search_available_products for open-ended category-wide cheapest or
        most expensive questions; this tool only compares the supplied IDs.

        Args:
            product_ids: Distinct product codes from current catalog results.
            fields: Any of original_price, payable_price, and stock_quantity.
            payment_method: standard unless the customer explicitly asks for PIX pricing.
        """
        request = ProductComparisonRequest(
            product_ids=tuple(product_ids),
            fields=tuple(fields),
            payment_method=payment_method,
        )
        trace("tool.called", tool="compare_products", product_count=len(product_ids))
        lookup = self.repository.lookup_many(
            ProductBatchLookupQuery(
                product_ids=request.product_ids,
                payment_method=payment_method,
            )
        )
        result = calculate_comparison(request, lookup)
        trace(
            "tool.result",
            tool="compare_products",
            status=result.status,
            comparison_count=len(result.comparisons),
        )
        return {
            **result.model_dump(mode="json"),
            "price_basis": "computed_quote",
            "inventory_basis": "simulated_current",
        }


def quote_tools(repository: ProductRepository) -> list[Tool]:
    tools = ProductQuoteTools(repository)
    return [Tool(tools.calculate_quote), Tool(tools.compare_products)]
