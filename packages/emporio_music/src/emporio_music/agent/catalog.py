"""Grounded product-search tool and catalog-agent composition."""

from typing import Annotated

from pydantic import Field, StrictBool
from pydantic_ai import ModelRetry, Tool
from pydantic_ai.models import Model

from emporio_music.agent.amounts import BRLAmount, brl_to_centavos
from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.factory import create_agent
from emporio_music.agent.quotes import quote_tools
from emporio_music.agent.settings import AgentSettings
from emporio_music.diagnostics import trace
from emporio_music.domain.base import NonblankText
from emporio_music.domain.catalog import ProductSearchQuery, ProductSortOrder
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.pricing import PaymentMethod
from emporio_music.ports.catalog import ProductRepository


class ProductSearchTool:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def search_available_products(
        self,
        payment_method: PaymentMethod,
        category: NonblankText | None = None,
        product_name: NonblankText | None = None,
        min_price_brl: BRLAmount | None = None,
        max_price_brl: BRLAmount | None = None,
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10,
        promotions_only: StrictBool = False,
        sort_order: ProductSortOrder = "price_asc",
    ) -> dict[str, object]:
        """Find available instruments for requested recommendations, by category, budget or partial name.

        For an initial named product, use find_product_by_name; for a known code use get_product_details.
        Use find_product_alternatives for substitutes without a customer budget.
        Do not search alternatives to a named product unless the customer asks.
        For alternatives, use the category and customer-requested budget; omit
        product_name unless the customer explicitly restricts alternatives by name.
        Keeping the unavailable model name would exclude other products.
        Use price_asc for cheapest questions and price_desc for most-expensive
        questions. Both sort by payable price with product ID as a stable tie-breaker.
        Use calculate_quote for exact totals and compare_products only after products
        have been identified.

        Args:
            category: Instrument category, e.g. Violões, not an individual model name.
            product_name: Partial product/model name, e.g. Takamine GD20.
            min_price_brl: Inclusive payable-price minimum in reais, up to 1 billion, NOT centavos.
            max_price_brl: Inclusive payable-price maximum in reais, up to 1 billion, NOT centavos.
            limit: Maximum returned products, 1–20. Total count includes omitted matches.
            payment_method: standard unless the customer explicitly requests pix pricing.
            promotions_only: Return only eligible active promotional products, not PIX-only discounts.
            sort_order: Sort by payable price ascending or descending; ties use product ID.
        """
        trace(
            "tool.called",
            tool="search_available_products",
            limit=limit,
        )
        query = ProductSearchQuery(
            category=category,
            product_name=product_name,
            min_price_centavos=brl_to_centavos(min_price_brl),
            max_price_centavos=brl_to_centavos(max_price_brl),
            available_only=True,
            payment_method=payment_method,
            promotions_only=promotions_only,
            limit=limit,
            sort_order=sort_order,
        )
        return self._search(query)

    def find_product_by_name(
        self,
        product_name: NonblankText,
        payment_method: PaymentMethod,
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10,
    ) -> dict[str, object]:
        """Initial named-product lookup, including unavailable products.

        Return codes for disambiguation. Once the product is identified, use
        get_product_details(product_id, payment_method) for every fresh follow-up.
        Set payment_method=pix only for an explicit PIX request, otherwise standard.
        """
        trace("tool.called", tool="find_product_by_name", limit=limit)
        return self._search(
            ProductSearchQuery(
                product_name=product_name,
                available_only=False,
                limit=limit,
                payment_method=payment_method,
            )
        )

    def get_product_details(
        self,
        product_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)],
        payment_method: PaymentMethod,
    ) -> dict[str, object]:
        """Read fresh price, stock and specs for an identified product code.

        Resolve ordinal references using codes in the previous answer. This tool
        accepts no names. Set pix for an explicit PIX request, otherwise standard.
        """
        trace("tool.called", tool="get_product_details")
        return self._search(
            ProductSearchQuery(
                product_id=product_id,
                available_only=False,
                limit=1,
                payment_method=payment_method,
            )
        )

    def find_product_alternatives(
        self,
        product_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)],
        payment_method: PaymentMethod,
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 5,
    ) -> dict[str, object]:
        """Find available alternatives when the customer asks for a substitute.

        Use the product_id from the original detail lookup. The category comes
        from the catalog; no budget or product-name restriction is inferred.
        Set pix for an explicit PIX request, otherwise standard.
        If the customer provides a budget, use search_available_products instead.
        """
        original = self.repository.search(
            ProductSearchQuery(
                product_id=product_id,
                payment_method=payment_method,
                available_only=False,
                limit=1,
            ),
        )
        if not original.products:
            raise ModelRetry(
                "Original product not found; look up its exact name first."
            )
        trace("tool.called", tool="find_product_alternatives")
        return self._search(
            ProductSearchQuery(
                category=original.products[0].category_name,
                exclude_product_id=product_id,
                payment_method=payment_method,
                limit=limit,
            )
        )

    def _search(self, query: ProductSearchQuery) -> dict[str, object]:
        result = self.repository.search(query)
        trace(
            "tool.result",
            total_matches=result.total_matches,
            returned=len(result.products),
        )
        products: list[dict[str, object]] = []
        for item in result.products:
            row = item.model_dump(mode="json")
            row["price_brl"] = (
                f"{item.price_centavos // 100}.{item.price_centavos % 100:02d}"
            )
            products.append(row)
        return {
            "products": products,
            "total_matches": result.total_matches,
            "truncated": result.truncated,
            "price_basis": "computed_quote",
            "promotion_validity_basis": "current_simulated_catalog",
            "inventory_basis": "simulated_current",
        }


def create_catalog_agent(
    settings: AgentSettings,
    repository: ProductRepository,
    *,
    model: Model | None = None,
) -> PydanticAgentExecutor:
    return create_agent(
        settings,
        model=model,
        tools=product_tools(repository),
    )


def product_tools(repository: ProductRepository) -> list[Tool[ExecutionContext]]:
    tools = ProductSearchTool(repository)
    return [
        Tool(tools.search_available_products),
        Tool(tools.find_product_by_name),
        Tool(tools.get_product_details),
        Tool(tools.find_product_alternatives),
        *quote_tools(repository),
    ]
