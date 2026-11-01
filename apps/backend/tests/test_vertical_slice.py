"""High-risk catalog facts across the complete offline HTTP/tool/SQLite boundary."""

import asyncio
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
from emporio_music_backend.contracts import (
    ChatRequest,
    ConversationMessage,
    CustomerIdentity,
    ExecutionContext,
)
from emporio_music_backend.infrastructure.catalog_import import import_catalog
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
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
    conversations: SQLiteConversationRepository,
    api_headers: dict[str, str],
    tool_name: str,
    arguments: dict[str, object],
    total: int,
    price: int | None,
    stock: int | None,
) -> None:
    data = Path(__file__).parents[3] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(
        data / "products.csv",
        data / "categories.csv",
        data / "promotions.csv",
        database,
    )
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
    with TestClient(create_app(ChatService(executor, conversations))) as client:
        client.headers.update(api_headers)
        response = client.post("/api/chat", json={"message": "Consulta de integração"})
    assert response.status_code == 200
    if total > 10:
        assert response.json()["answer"].startswith(answer)
        assert (
            "seleção" in response.json()["answer"]
            and str(total) in response.json()["answer"]
        )
    else:
        assert response.json()["answer"] == answer
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


def test_direct_history_uses_fresh_catalog_results_without_replaying_old_notices(
    tmp_path: Path,
    conversations: SQLiteConversationRepository,
) -> None:
    data = Path(__file__).parents[3] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(
        data / "products.csv",
        data / "categories.csv",
        data / "promotions.csv",
        database,
    )
    identity = CustomerIdentity(customer_id=1)
    context = ExecutionContext(
        identity=identity,
        session=conversations.create(identity),
        history=(
            ConversationMessage(role="user", content="Quais violões vocês têm?"),
            ConversationMessage(
                role="assistant",
                content="GD20 por R$1,00. Seleção de 12 opções, lista incompleta.",
            ),
        ),
    )
    assert context.session is not None
    conversations.append(
        context.session,
        user_message=context.history[0].content,
        answer=context.history[1].content,
    )
    observed: list[int] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returned = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returned:
            return ModelResponse(
                parts=[ToolCallPart("get_product_details", {"product_name": "GD20"})]
            )
        assert isinstance(returned[-1].content, dict)
        payload: dict[str, Any] = dict(returned[-1].content)
        observed.append(payload["products"][0]["price_centavos"])
        return ModelResponse(parts=[TextPart("Resposta de controle da nova consulta")])

    executor = create_catalog_agent(
        AgentSettings(), SQLiteProductRepository(database), model=FunctionModel(model)
    )
    response = asyncio.run(
        ChatService(executor, conversations).chat(
            ChatRequest(
                message="E quanto custa agora?", session_id=context.session.session_id
            ),
            context=ExecutionContext(identity=identity),
        )
    )
    assert observed == [219900]
    assert response.answer == "Resposta de controle da nova consulta"
