"""Offline promotion/PIX follow-ups through fixed demo application composition."""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Any

import emporio_music.composition as composition
import emporio_music_api.app as api_app
import httpx
import pytest
from emporio_music import paths
from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.settings import AgentSettings
from emporio_music.infrastructure.catalog_import import (
    PROMOTION_COLUMNS,
    import_catalog,
)
from emporio_music.ports.catalog import ProductRepository
from emporio_music.ports.orders import OrderRepository
from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from tests._support import REPOSITORY_ROOT

DATA = REPOSITORY_ROOT / "data"
INVENTORY_NOTICE = (
    "Preços e estoque refletem uma fotografia importada do catálogo; "
    "não há confirmação em tempo real."
)


def test_promotion_history_pix_refresh_concurrent_quotes_and_failed_turns(
    tmp_path: Path,
    operational_database: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(paths, "OPERATIONS_DATABASE_PATH", operational_database)
    catalog = operational_database.parent / "operational-catalog.sqlite3"
    conversations = tmp_path / "conversations.sqlite3"
    monkeypatch.setattr(paths, "CATALOG_DATABASE_PATH", catalog)
    monkeypatch.setattr(paths, "CONVERSATION_DATABASE_PATH", conversations)
    monkeypatch.setenv("PIPELINE_LOGS", "1")
    monkeypatch.setattr(logging.getLogger("emporio.pipeline"), "propagate", True)
    observed: list[dict[str, Any]] = []

    async def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        await asyncio.sleep(0)
        returns = [
            p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
        ]
        prompt = [
            p.content
            for m in messages
            for p in m.parts
            if isinstance(p, UserPromptPart)
        ][-1]
        answers = [
            p.content for m in messages for p in m.parts if isinstance(p, TextPart)
        ]
        if not returns:
            if prompt == "Promoções?":
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "search_available_products",
                            {
                                "payment_method": "standard",
                                "promotions_only": True,
                                "limit": 2,
                            },
                        )
                    ]
                )
            if prompt == "E o segundo no PIX?":
                assert answers[0].splitlines()[1] == "2. Ohana CK-20 Concert Natural"
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "find_product_by_name",
                            {
                                "product_name": answers[0]
                                .splitlines()[1]
                                .removeprefix("2. "),
                                "payment_method": "pix",
                            },
                        )
                    ]
                )
            if prompt == "Falhar consulta":
                with sqlite3.connect(catalog) as conn:
                    conn.execute("DROP TABLE promotions")
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "find_product_by_name",
                            {"payment_method": "standard", "product_name": "GD20"},
                        )
                    ]
                )
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "find_product_by_name",
                        {
                            "product_name": "GD20",
                            "payment_method": "pix"
                            if prompt == "GD20 PIX"
                            else "standard",
                        },
                    )
                ]
            )
        assert isinstance(returns[-1].content, dict)
        payload = dict(returns[-1].content)
        observed.append(payload)
        if prompt == "Promoções?":
            assert [p["product_id"] for p in payload["products"]] == [127, 121]
            return ModelResponse(
                parts=[
                    TextPart(
                        "\n".join(
                            f"{index}. {p['name']}"
                            for index, p in enumerate(payload["products"], 1)
                        )
                        + "\n\n"
                        + "\n".join(
                            f"R$ {p['price_brl'].replace('.', ',')}; "
                            f"{p['pricing']['discount_percent']}%; "
                            f"final R$ {p['pricing']['final_price_brl'].replace('.', ',')}"
                            for p in payload["products"]
                        )
                    )
                ]
            )
        return ModelResponse(
            parts=[
                TextPart(
                    "Consulta atual: "
                    + payload["products"][0]["pricing"]["final_price_brl"]
                    + (
                        f"; desconto: {payload['products'][0]['pricing']['discount_percent']}%"
                        if payload["products"][0]["pricing"]["discount_percent"]
                        else ""
                    )
                )
            ]
        )

    def factory(
        settings: AgentSettings, products: ProductRepository, orders: OrderRepository
    ) -> PydanticAgentExecutor:
        return create_store_agent(
            settings, products, orders, model=FunctionModel(model)
        )

    monkeypatch.setattr(composition, "create_store_agent", factory)
    app = api_app.create_app()
    with TestClient(app) as client:
        first = client.post("/api/chat", json={"message": "Promoções?"})
        assert first.status_code == 200
        answer = first.json()["answer"]
        assert "359,00" in answer and "323,10" in answer and "10%" in answer
        assert "549,00" in answer and "439,20" in answer and "20%" in answer
        assert answer.count("323,10") == answer.count("439,20") == 1
        assert "seleção" in answer and "4" in answer and "fotografia" not in answer
        session = first.json()["session_id"]
        followup = client.post(
            "/api/chat",
            json={
                "message": "E o segundo no PIX?",
                "session_id": session,
            },
        )
        assert followup.status_code == 200
        assert followup.json()["answer"].startswith("Consulta atual: 439.20")
        assert observed[-1]["products"][0]["pricing"]["discount_percent"] == 20
        assert observed[-1]["products"][0]["pricing"]["discount_kind"] == "promotion"
        assert "323,10" not in followup.json()["answer"]
        assert (
            client.post(
                "/api/chat",
                json={"message": "Olá", "payment_method": "pix"},
            ).status_code
            == 422
        )
    # Independent temporary snapshot with no offers; never edit the supplied CSV.
    no_offers = tmp_path / "independent-empty-promotions.csv"
    no_offers.write_text(",".join(PROMOTION_COLUMNS) + "\n")
    import_catalog(
        DATA / "catalog" / "products.csv",
        DATA / "catalog" / "categories.csv",
        no_offers,
        catalog,
    )
    app = api_app.create_app()
    with TestClient(app) as client:
        refreshed = client.post(
            "/api/chat",
            json={
                "message": "E o segundo no PIX?",
                "session_id": session,
            },
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["answer"].startswith("Consulta atual: 521.55")
        assert (
            "5%" in refreshed.json()["answer"]
            and "20%" not in refreshed.json()["answer"]
        )

    async def concurrent() -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            results = await asyncio.gather(
                *(
                    client.post("/api/chat", json={"message": message})
                    for message in ("GD20", "GD20 PIX")
                )
            )
        assert results[0].status_code == results[1].status_code == 200
        assert results[0].json()["answer"] == "Consulta atual: 2199.00"
        assert results[1].json()["answer"].startswith("Consulta atual: 2089.05")

    asyncio.run(concurrent())
    with TestClient(app) as client:
        failed = client.post(
            "/api/chat",
            json={"message": "Falhar consulta", "session_id": session},
        )
        assert failed.status_code == 500 and failed.json() == {
            "detail": "Conversation failed"
        }
    with sqlite3.connect(conversations) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM turns WHERE session_id=?", (session,)
            ).fetchone()[0]
            == 3
        )
    with sqlite3.connect(operational_database) as conn:
        assert (
            conn.execute(
                "SELECT total_centavos FROM orders WHERE order_id=4"
            ).fetchone()[0]
            == 79990
        )
    for secret in (
        session,
        "Kalani",
        "Ohana",
        "439.20",
        "521.55",
        "product_name",
        "customer_id",
    ):
        assert secret not in caplog.text
    assert all(
        p["promotion_validity_basis"] == "current_simulated_catalog" for p in observed
    )
