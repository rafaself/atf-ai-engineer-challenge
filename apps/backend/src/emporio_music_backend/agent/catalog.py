"""Grounded product-search tool and catalog-agent composition."""

from decimal import Decimal, localcontext
from typing import Annotated

from pydantic import Field, TypeAdapter
from pydantic_ai import Tool
from pydantic_ai.models import Model

from emporio_music_backend.agent.factory import PydanticAgentExecutor, create_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts import NonblankText, ProductSearchQuery
from emporio_music_backend.ports import ProductRepository

BRLAmount = Annotated[
    Decimal,
    Field(
        ge=0,
        le=Decimal("92233720368547758.07"),
        max_digits=19,
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
    ) -> dict[str, object]:
        """Find available instruments for recommendations, by category, budget or partial name.

        For price/stock/status details about a named product, use get_product_details.

        Args:
            category: Instrument category, e.g. Violões, not an individual model name.
            product_name: Partial product/model name, e.g. Takamine GD20.
            min_price_brl: Inclusive minimum in Brazilian reais, NOT centavos.
            max_price_brl: Inclusive maximum in Brazilian reais, NOT centavos.
            limit: Maximum returned products, 1–20. Total count includes omitted matches.
        """
        query = ProductSearchQuery(
            category=category,
            product_name=product_name,
            min_price_centavos=_centavos(min_price_brl),
            max_price_centavos=_centavos(max_price_brl),
            available_only=True,
            limit=limit,
        )
        return self._search(query)

    def get_product_details(
        self,
        product_name: NonblankText,
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10,
    ) -> dict[str, object]:
        """Look up named products, including out-of-stock/discontinued/coming-soon.

        Use for price, stock and status questions, even if availability is unknown.
        Report actual stock/status; multiple partial-name matches remain visible.
        """
        return self._search(
            ProductSearchQuery(
                product_name=product_name, available_only=False, limit=limit
            )
        )

    def _search(self, query: ProductSearchQuery) -> dict[str, object]:
        result = self.repository.search(query)
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
            "price_basis": "catalog",
            "inventory_basis": "imported_snapshot",
        }


def create_catalog_agent(
    settings: AgentSettings,
    repository: ProductRepository,
    *,
    model: Model | None = None,
) -> PydanticAgentExecutor:
    tools = ProductSearchTool(repository)
    return create_agent(
        settings,
        model=model,
        tools=[Tool(tools.search_available_products), Tool(tools.get_product_details)],
    )
