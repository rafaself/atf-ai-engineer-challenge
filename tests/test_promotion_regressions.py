"""Missing promotion pricing and transparency must fail before implementation."""

from pathlib import Path

import pytest
from emporio_music.agent.catalog import ProductSearchTool
from emporio_music.agent.output import customer_answer
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.infrastructure.catalog_import import import_catalog
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage


def test_supplied_active_offer_is_quoted_separately_from_original_price(
    tmp_path: Path,
) -> None:
    data = Path(__file__).resolve().parents[1] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(
        data / "products.csv",
        data / "categories.csv",
        data / "promotions.csv",
        database,
    )
    result = ProductSearchTool(SQLiteProductRepository(database)).find_product_by_name(
        "Kalani KAL-700T", payment_method="standard"
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
        "explanation": "Promoção de 10%.",
        "promotion_id": 12,
        "promotion_description": "Oferta Especial",
    }


@pytest.mark.parametrize("discount_kind", ["promotion", "none"])
def test_discount_disclosure_uses_current_run_evidence_only(
    discount_kind: str,
) -> None:
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
    if discount_kind == "none":
        product = {**product, "pricing": {"discount_kind": "none"}}
    ctx = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart("find_product_by_name", {"products": [historical]})
                ],
                run_id="old",
            ),
            ModelRequest(
                parts=[ToolReturnPart("find_product_by_name", {"products": [product]})],
                run_id="current",
            ),
        ],
    )
    answer = customer_answer(ctx, "Oferta consultada.")
    assert answer.startswith("Oferta consultada.")
    assert "fotografia" not in answer
    assert "Historical offer" not in answer and "Kalani" not in answer
