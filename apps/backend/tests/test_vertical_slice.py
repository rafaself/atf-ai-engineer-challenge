"""High-risk catalog facts across the complete offline HTTP/tool/SQLite boundary."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from emporio_music_backend.agent.catalog import create_catalog_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.api.app import create_app
from emporio_music_backend.application import ChatService
from emporio_music_backend.infrastructure.catalog_import import import_catalog
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)


@pytest.mark.parametrize(
    ("tool_name", "arguments", "total", "price", "stock"),
    [
        (
            "search_available_products",
            {"category": "violões", "max_price_brl": 1000},
            12,
            None,
            None,
        ),
        ("get_product_details", {"product_name": "Takamine GD20"}, 1, 219900, 5),
        (
            "search_available_products",
            {"product_name": "Giannini GF-3D"},
            0,
            None,
            None,
        ),
        (
            "get_product_details",
            {"product_name": "Giannini GF-3D"},
            1,
            None,
            0,
        ),
        ("get_product_details", {"product_name": "ZXQ-999-Inexistente"}, 0, None, None),
    ],
)
def test_snapshot_facts_survive_http_agent_tool_pipeline(
    tmp_path: Path,
    tool_name: str,
    arguments: dict[str, object],
    total: int,
    price: int | None,
    stock: int | None,
) -> None:
    data = Path(__file__).parents[3] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(data / "products.csv", data / "categories.csv", database)
    observed: list[dict[str, Any]] = []
    answer = "Resposta de controle; não é avaliação LLM."

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returned = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returned:
            return ModelResponse(parts=[ToolCallPart(tool_name, arguments)])
        assert isinstance(returned[-1].content, dict)
        observed.append(dict(returned[-1].content))
        return ModelResponse(parts=[TextPart(answer)])

    executor = create_catalog_agent(
        AgentSettings(), SQLiteProductRepository(database), model=FunctionModel(model)
    )
    with TestClient(create_app(ChatService(executor))) as client:
        response = client.post("/api/chat", json={"message": "Consulta de integração"})
    assert response.status_code == 200
    if total > 10:
        assert response.json()["answer"].startswith(answer)
        assert (
            "seleção" in response.json()["answer"]
            and str(total) in response.json()["answer"]
        )
    else:
        assert response.json() == {"answer": answer}
    assert len(observed) == 1
    result = observed[0]
    assert result["total_matches"] == total
    products = result["products"]
    assert len(products) == min(total, 10)
    assert result["truncated"] == (total > 10)
    if "category" in arguments:
        assert all(p["available"] and p["price_centavos"] <= 100000 for p in products)
        assert [(p["price_centavos"], p["product_id"]) for p in products] == sorted(
            (p["price_centavos"], p["product_id"]) for p in products
        )
    if price is not None:
        assert products[0]["price_centavos"] == price
        assert products[0]["price_brl"] == "2199.00"
    if stock is not None:
        assert products[0]["stock_quantity"] == stock
        assert products[0]["available"] == (stock > 0)
