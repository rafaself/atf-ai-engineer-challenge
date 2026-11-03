"""Grounded product-search tool and catalog-agent composition."""

from decimal import Decimal, localcontext
from typing import Annotated

from pydantic import Field, StrictBool, TypeAdapter
from pydantic_ai import ModelRetry, Tool
from pydantic_ai.models import Model

from emporio_music_backend.agent.factory import PydanticAgentExecutor, create_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts.base import NonblankText
from emporio_music_backend.contracts.catalog import ProductSearchQuery
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.pricing import PaymentMethod
from emporio_music_backend.diagnostics import trace
from emporio_music_backend.ports.catalog import ProductRepository

BRLAmount = Annotated[
    Decimal,
    Field(
        ge=0,
        le=Decimal("1000000000"),
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
    ),
]
_amount = TypeAdapter(BRLAmount)


def _centavos(value: Decimal | None) -> int | None:
    if value is None:
        return None
    # Validation bounds precision and magnitude before multiplication/conversion.
    amount = _amount.validate_python(value)
    with localcontext() as context:
        context.prec = 21
        return int(amount * 100)


class ProductSearchTool:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def search_available_products(
        self,
        category: NonblankText | None = None,
        product_name: NonblankText | None = None,
        min_price_brl: BRLAmount | None = None,
        max_price_brl: BRLAmount | None = None,
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10,
        payment_method: PaymentMethod = "standard",
        promotions_only: StrictBool = False,
    ) -> dict[str, object]:
        """Find available instruments for requested recommendations, by category, budget or partial name.

        For price/stock/status/specifications about a named product, use get_product_details.
        Use find_product_alternatives for substitutes without a customer budget.
        Do not search alternatives to a named product unless the customer asks.
        For alternatives, use the category and customer-requested budget; omit
        product_name unless the customer explicitly restricts alternatives by name.
        Keeping the unavailable model name would exclude other products.

        Args:
            category: Instrument category, e.g. Violões, not an individual model name.
            product_name: Partial product/model name, e.g. Takamine GD20.
            min_price_brl: Inclusive payable-price minimum in reais, up to 1 billion, NOT centavos.
            max_price_brl: Inclusive payable-price maximum in reais, up to 1 billion, NOT centavos.
            limit: Maximum returned products, 1–20. Total count includes omitted matches.
            payment_method: standard unless the customer explicitly requests pix pricing.
            promotions_only: Return only eligible active promotional products, not PIX-only discounts.
        """
        trace(
            "tool.called",
            tool="search_available_products",
            limit=limit,
        )
        query = ProductSearchQuery(
            category=category,
            product_name=product_name,
            min_price_centavos=_centavos(min_price_brl),
            max_price_centavos=_centavos(max_price_brl),
            available_only=True,
            payment_method=payment_method,
            promotions_only=promotions_only,
            limit=limit,
        )
        return self._search(query)

    def get_product_details(
        self,
        product_name: NonblankText | None = None,
        product_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
        | None = None,
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10,
        payment_method: PaymentMethod = "standard",
    ) -> dict[str, object]:
        """Look up a named product, including out-of-stock/discontinued/coming-soon.

        Use for price, stock, status and structured catalog specifications, even if availability is unknown.
        For follow-ups, use product_id from the prior result, not a rewritten name.
        Provide exactly one of product_name (initial lookup) or product_id (follow-up).
        One lookup is sufficient for the named product. Do not also search for it
        unless the customer asks for alternatives. Report returned fields only;
        multiple partial-name matches remain visible.
        """
        if (product_name is None) == (product_id is None):
            raise ModelRetry("Provide exactly one of product_name or product_id.")
        trace(
            "tool.called",
            tool="get_product_details",
            limit=limit,
        )
        return self._search(
            ProductSearchQuery(
                product_name=product_name,
                product_id=product_id,
                available_only=False,
                limit=limit,
                payment_method=payment_method,
            )
        )

    def find_product_alternatives(
        self,
        product_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)],
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 5,
    ) -> dict[str, object]:
        """Find available alternatives when the customer asks for a substitute.

        Use the product_id from the original detail lookup. The category comes
        from the catalog; no budget or product-name restriction is inferred.
        If the customer provides a budget, use search_available_products instead.
        """
        original = self.repository.search(
            ProductSearchQuery(
                product_id=product_id,
                available_only=False,
                limit=1,
            )
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
        Tool(tools.get_product_details),
        Tool(tools.find_product_alternatives),
    ]
