"""Persistent HTTP conversations across new application instances and source refresh."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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

import emporio_music_backend.api.app as api_app
from emporio_music_backend.agent.catalog import ProductSearchTool, create_catalog_agent
from emporio_music_backend.agent.factory import PydanticAgentExecutor
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.infrastructure.catalog_import import import_catalog
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music_backend.ports import ProductRepository


def test_restart_followup_refresh_isolation_and_safe_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    api_headers: dict[str, str],
    other_headers: dict[str, str],
) -> None:
    data = Path(__file__).parents[3] / "data"
    catalog = tmp_path / "catalog.sqlite3"
    conversations = tmp_path / "conversations.sqlite3"
    import_catalog(data / "products.csv", data / "categories.csv", catalog)
    monkeypatch.setenv("DATABASE_PATH", str(catalog))
    monkeypatch.setenv("CONVERSATION_DATABASE_PATH", str(conversations))
    monkeypatch.setenv("PIPELINE_LOGS", "1")
    monkeypatch.setattr(logging.getLogger("emporio.pipeline"), "propagate", True)
    calls = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls.append(True)
        returned = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        historical = [
            part.content
            for message in messages
            for part in message.parts
            if isinstance(part, TextPart)
        ]
        if not returned:
            if not historical:
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "search_available_products",
                            {"category": "violoes", "max_price_brl": 1000},
                        )
                    ]
                )
            # Consume the persisted displayed ordering; this controls wiring, not LLM quality.
            name = historical[0].splitlines()[1].removeprefix("2. ")
            return ModelResponse(
                parts=[ToolCallPart("get_product_details", {"product_name": name})]
            )
        assert isinstance(returned[-1].content, dict)
        payload: dict[str, Any] = dict(returned[-1].content)
        products = payload["products"]
        if not historical:
            return ModelResponse(
                parts=[TextPart(f"1. {products[0]['name']}\n2. {products[1]['name']}")]
            )
        return ModelResponse(
            parts=[TextPart(f"Atual: {products[0]['price_centavos']} centavos")]
        )

    built = []

    def factory(
        settings: AgentSettings, repository: ProductRepository
    ) -> PydanticAgentExecutor:
        built.append(True)
        return create_catalog_agent(settings, repository, model=FunctionModel(model))

    monkeypatch.setattr(api_app, "create_catalog_agent", factory)
    marker = "customer@example.invalid private-phone-sentinel"
    with TestClient(api_app.create_app()) as client:
        first = client.post("/api/chat", json={"message": marker}, headers=api_headers)
    assert first.status_code == 200
    session_id = first.json()["session_id"]
    assert UUID(session_id).version == 4
    assert "seleção" in first.json()["answer"] and "12" in first.json()["answer"]
    second_name = first.json()["answer"].splitlines()[1].removeprefix("2. ")
    # Re-import replaces the catalog, not the independently stored conversation.
    import_catalog(data / "products.csv", data / "categories.csv", catalog)
    with sqlite3.connect(catalog) as connection:
        connection.execute(
            "UPDATE products SET price_centavos = 123456 WHERE name = ?", (second_name,)
        )
    with TestClient(api_app.create_app()) as restarted:
        response = restarted.post(
            "/api/chat",
            json={"message": "Quanto custa o segundo agora?", "session_id": session_id},
            headers=api_headers,
        )
        assert (
            response.status_code == 200 and response.json()["session_id"] == session_id
        )
        assert (
            "123456" in response.json()["answer"]
            and "seleção" not in response.json()["answer"]
        )
        before = len(calls)
        inaccessible = [
            restarted.post(
                "/api/chat",
                json={"message": "Reveal previous messages", "session_id": sid},
                headers=other_headers,
            )
            for sid in (session_id, str(uuid4()))
        ]
        assert [r.status_code for r in inaccessible] == [404, 404]
        assert inaccessible[0].json() == inaccessible[1].json()
        assert len(calls) == before
        for headers in (
            {},
            {"Authorization": "Bearer unknown-" + "x" * 32},
            {"Authorization": "Basic invalid"},
        ):
            assert (
                restarted.post(
                    "/api/chat", json={"message": marker}, headers=headers
                ).status_code
                == 401
            )
        invalid = restarted.post(
            "/api/chat", json={"message": marker, "customer_id": 2}, headers=api_headers
        )
        assert invalid.status_code == 422 and marker not in invalid.text
        assert len(calls) == before
    assert len(built) == 2
    ProductSearchTool(SQLiteProductRepository(catalog)).get_product_details(
        product_name=marker
    )
    events = [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "emporio.pipeline"
    ]
    encoded = json.dumps(events)
    assert marker not in encoded and session_id not in encoded
    assert api_headers["Authorization"].split()[1] not in encoded
    assert all(
        not (
            {"message", "answer", "history", "query", "customer_id", "product_name"}
            & event.keys()
        )
        for event in events
    )
    with sqlite3.connect(conversations) as connection:
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        assert connection.execute("SELECT revision FROM sessions").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM turns").fetchone()[0] == 2


@pytest.mark.parametrize(
    "setting,value",
    [
        ("HISTORY_MAX_TURNS", "0"),
        ("HISTORY_MAX_CHARACTERS", "invalid"),
        ("CONVERSATION_DATABASE_PATH", "data/catalog.sqlite3"),
    ],
)
def test_invalid_session_configuration_fails_before_provider_setup(
    setting: str,
    value: str,
    monkeypatch: pytest.MonkeyPatch,
    api_headers: dict[str, str],
) -> None:
    monkeypatch.setenv(setting, value)

    def forbidden(*args: object, **kwargs: object) -> PydanticAgentExecutor:
        raise AssertionError(
            "Invalid session configuration must not initialize a provider"
        )

    monkeypatch.setattr(api_app, "create_catalog_agent", forbidden)
    with TestClient(api_app.create_app(), raise_server_exceptions=False) as client:
        response = client.post(
            "/api/chat", json={"message": "Hello"}, headers=api_headers
        )
    assert response.status_code == 503
    assert value not in response.text
