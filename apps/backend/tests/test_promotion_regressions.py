"""Missing promotion pricing and transparency must fail before implementation."""

from pathlib import Path

from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from emporio_music_backend.agent.catalog import ProductSearchTool
from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.contracts import ExecutionContext
from emporio_music_backend.infrastructure.catalog_import import import_catalog
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)


def test_supplied_active_offer_is_quoted_separately_from_original_price(
    tmp_path: Path,
) -> None:
    data = Path(__file__).parents[3] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(
        data / "products.csv",
        data / "categories.csv",
        data / "promotions.csv",
        database,
    )
    result = ProductSearchTool(SQLiteProductRepository(database)).get_product_details(
        "Kalani KAL-700T"
    )
    products = result["products"]
    assert isinstance(products, list)
    assert products[0]["price_centavos"] == 35900
    assert products[0].get("pricing") == {
        "payment_method": "standard",
        "final_price_centavos": 32310,
        "final_price_brl": "323.10",
        "discount_percent": 10,
        "discount_kind": "promotion",
        "promotion_id": 12,
        "promotion_description": "Oferta Especial",
    }


def test_discount_disclosure_uses_current_run_evidence_only() -> None:
    product = {
        "product_id": 127,
        "name": "Kalani KAL-700T",
        "price_brl": "359.00",
        "pricing": {
            "final_price_brl": "323.10",
            "discount_percent": 10,
            "discount_kind": "promotion",
            "payment_method": "standard",
        },
    }
    historical = {**product, "name": "Historical offer"}
    ctx = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart("get_product_details", {"products": [historical]})
                ],
                run_id="old",
            ),
            ModelRequest(
                parts=[ToolReturnPart("get_product_details", {"products": [product]})],
                run_id="current",
            ),
        ],
    )
    answer = customer_answer(ctx, "Oferta consultada.")
    assert "359,00" in answer and "323,10" in answer and "10%" in answer
    assert "fotografia" in answer and "Historical offer" not in answer
