"""Grounded product-search tool and catalog-agent composition."""

from decimal import Decimal, localcontext
from typing import Annotated

from pydantic import Field, StrictBool, TypeAdapter
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

    def search_products(
        self,
        category: NonblankText | None = None,
        product_name: NonblankText | None = None,
        min_price_brl: BRLAmount | None = None,
        max_price_brl: BRLAmount | None = None,
        available_only: StrictBool = True,
        limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10,
    ) -> dict[str, object]:
        """Search the imported instrument catalog; never invent catalog facts.

        Args:
            category: Instrument category, e.g. Violões, not an individual model name.
            product_name: Partial product/model name, e.g. Takamine GD20.
            min_price_brl: Inclusive minimum in Brazilian reais, NOT centavos.
            max_price_brl: Inclusive maximum in Brazilian reais, NOT centavos.
            available_only: True for recommendations; False to explain named unavailable items.
            limit: Maximum returned products, 1–20. Total count includes omitted matches.
        """
        query = ProductSearchQuery(
            category=category,
            product_name=product_name,
            min_price_centavos=_centavos(min_price_brl),
            max_price_centavos=_centavos(max_price_brl),
            available_only=available_only,
            limit=limit,
        )
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
    return create_agent(
        settings,
        model=model,
        tools=[Tool(ProductSearchTool(repository).search_products)],
    )
