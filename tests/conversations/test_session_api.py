"""Persistent HTTP conversations across new application instances and source refresh."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import emporio_music.composition as composition
import emporio_music_api.app as api_app
import pytest
from emporio_music import paths
from emporio_music.agent.catalog import ProductSearchTool
from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.settings import AgentSettings
from emporio_music.application.chat import ChatService
from emporio_music.domain.chat import AgentResponse, ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.catalog_import import import_catalog
from emporio_music.infrastructure.conversations import SQLiteConversationRepository
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music.ports.catalog import ProductRepository
from emporio_music.ports.orders import OrderRepository
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from tests._support import REPOSITORY_ROOT, run_async


class _UnusedAgent:
    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        raise AssertionError("History endpoints must not invoke the agent")


def test_restart_followup_refresh_isolation_and_safe_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    fixed_demo_identity: CustomerIdentity,
) -> None:
    data = REPOSITORY_ROOT / "data"
    catalog = tmp_path / "catalog.sqlite3"
    conversations = tmp_path / "conversations.sqlite3"
    import_catalog(
        data / "catalog" / "products.csv",
        data / "catalog" / "categories.csv",
        data / "catalog" / "promotions.csv",
        catalog,
    )
    monkeypatch.setattr(paths, "CATALOG_DATABASE_PATH", catalog)
    monkeypatch.setattr(paths, "CONVERSATION_DATABASE_PATH", conversations)
    stored = SQLiteConversationRepository(conversations)
    old_guest = stored.create(None)
    stored.append(old_guest, user_message="private guest history", answer="guest")
    old_foreign = stored.create(CustomerIdentity(customer_id=2))
    stored.append(old_foreign, user_message="private foreign history", answer="foreign")
    monkeypatch.setenv("PIPELINE_LOGS", "1")
    monkeypatch.setattr(logging.getLogger("emporio.pipeline"), "propagate", True)
    calls = []

    async def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
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
                            {
                                "payment_method": "standard",
                                "category": "violoes",
                                "max_price_brl": 1000,
                            },
                        )
                    ]
                )
            # Consume the persisted displayed ordering; this controls wiring, not LLM quality.
            name = historical[0].splitlines()[1].removeprefix("2. ")
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "find_product_by_name",
                        {"payment_method": "standard", "product_name": name},
                    )
                ]
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
        settings: AgentSettings, repository: ProductRepository, orders: OrderRepository
    ) -> PydanticAgentExecutor:
        built.append(True)
        return create_store_agent(
            settings, repository, orders, model=FunctionModel(model)
        )

    monkeypatch.setattr(composition, "create_store_agent", factory)
    marker = "customer@example.invalid private-phone-sentinel"
    with TestClient(api_app.create_app()) as client:
        first = client.post("/api/chat", json={"message": marker})
    assert first.status_code == 200
    session_id = first.json()["session_id"]
    assert UUID(session_id).version == 4
    assert "seleção" in first.json()["answer"] and "12" in first.json()["answer"]
    second_name = first.json()["answer"].splitlines()[1].removeprefix("2. ")
    # Re-import replaces the catalog, not the independently stored conversation.
    import_catalog(
        data / "catalog" / "products.csv",
        data / "catalog" / "categories.csv",
        data / "catalog" / "promotions.csv",
        catalog,
    )
    with sqlite3.connect(catalog) as connection:
        connection.execute(
            "UPDATE products SET price_centavos = 123456 WHERE name = ?", (second_name,)
        )
    with TestClient(api_app.create_app()) as restarted:
        response = restarted.post(
            "/api/chat",
            json={
                "message": "Quanto custa o segundo agora?",
                "session_id": session_id,
            },
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
                json={"message": "Reveal previous messages", "session_id": str(sid)},
            )
            for sid in (old_guest.session_id, old_foreign.session_id, uuid4())
        ]
        assert [r.status_code for r in inaccessible] == [404, 404, 404]
        assert all(
            response.json() == {"detail": "Conversation session unavailable"}
            for response in inaccessible
        )
        assert len(calls) == before
        invalid = restarted.post(
            "/api/chat",
            json={"message": marker, "customer_id": 2},
        )
        assert invalid.status_code == 422 and marker not in invalid.text
        assert len(calls) == before
    assert len(built) == 2
    ProductSearchTool(SQLiteProductRepository(catalog)).find_product_by_name(
        payment_method="standard", product_name=marker
    )
    events = [
        json.loads(r.getMessage())
        for r in caplog.records
        if r.name == "emporio.pipeline"
    ]
    encoded = json.dumps(events)
    assert marker not in encoded and session_id not in encoded
    assert all(
        not (
            {"message", "answer", "history", "query", "customer_id", "product_name"}
            & event.keys()
        )
        for event in events
    )
    with sqlite3.connect(conversations) as connection:
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM turns").fetchone()[0] == 4


def test_history_api_lists_loads_and_deletes_only_owned_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fixed_demo_identity: CustomerIdentity,
) -> None:
    conversations_path = tmp_path / "conversations.sqlite3"
    monkeypatch.setattr(paths, "CONVERSATION_DATABASE_PATH", conversations_path)
    repository = SQLiteConversationRepository(conversations_path)
    older = repository.create(fixed_demo_identity)
    repository.append(older, user_message="Primeira", answer="Resposta 1")
    repository.append(older, user_message="Continuação", answer="Resposta 2")
    newer = repository.create(fixed_demo_identity)
    repository.append(newer, user_message="Mais recente", answer="Resposta recente")
    empty = repository.create(fixed_demo_identity)
    foreign = repository.create(CustomerIdentity(customer_id=2))
    repository.append(foreign, user_message="Alheia", answer="Privada")
    service = ChatService(_UnusedAgent(), repository)

    async def run_in_test_thread(function: Any, *args: Any, **kwargs: Any) -> Any:
        return function(*args, **kwargs)

    monkeypatch.setattr(api_app, "run_in_threadpool", run_in_test_thread)
    test_app = api_app.create_app(chat_service=service)

    async def fixed_chat_service_factory() -> Any:
        return lambda: service

    test_app.dependency_overrides[api_app.get_chat_service_factory] = (
        fixed_chat_service_factory
    )

    async def exercise() -> None:
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            listed = await client.get("/api/conversations")
            assert listed.status_code == 200
            assert listed.json() == [
                {"session_id": str(newer.session_id), "title": "Mais recente"},
                {"session_id": str(older.session_id), "title": "Primeira"},
            ]

            loaded = await client.get(f"/api/conversations/{older.session_id}")
            assert loaded.status_code == 200
            assert loaded.json() == {
                "session_id": str(older.session_id),
                "messages": [
                    {"role": "user", "content": "Primeira"},
                    {"role": "assistant", "content": "Resposta 1"},
                    {"role": "user", "content": "Continuação"},
                    {"role": "assistant", "content": "Resposta 2"},
                ],
            }

            deleted = await client.delete(f"/api/conversations/{older.session_id}")
            assert deleted.status_code == 204
            listed_after_delete = await client.get("/api/conversations")
            assert [item["session_id"] for item in listed_after_delete.json()] == [
                str(newer.session_id)
            ]

            inaccessible = (
                older.session_id,
                foreign.session_id,
                empty.session_id,
                uuid4(),
            )
            responses = [
                await client.get(f"/api/conversations/{session_id}")
                for session_id in inaccessible
            ]
            assert [response.status_code for response in responses] == [404] * len(
                inaccessible
            )
            assert all(
                response.json() == {"detail": "Conversation session unavailable"}
                for response in responses
            )
            delete_responses = [
                await client.delete(f"/api/conversations/{foreign.session_id}"),
                await client.delete(f"/api/conversations/{uuid4()}"),
            ]
            assert [response.status_code for response in delete_responses] == [404, 404]
            assert all(
                response.json() == {"detail": "Conversation session unavailable"}
                for response in delete_responses
            )
            assert (
                await client.get("/api/conversations/not-a-uuid")
            ).status_code == 422
            assert (
                await client.delete("/api/conversations/not-a-uuid")
            ).status_code == 422

    run_async(exercise())
    with sqlite3.connect(conversations_path) as connection:
        assert connection.execute("SELECT count(*) FROM sessions").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM turns").fetchone()[0] == 2


@pytest.mark.parametrize(
    "setting,value",
    [
        ("HISTORY_MAX_TURNS", "0"),
        ("HISTORY_MAX_CHARACTERS", "invalid"),
    ],
)
def test_invalid_session_configuration_fails_before_provider_setup(
    setting: str,
    value: str,
    monkeypatch: pytest.MonkeyPatch,
    fixed_demo_identity: CustomerIdentity,
) -> None:
    monkeypatch.setenv(setting, value)

    def forbidden(*args: object, **kwargs: object) -> PydanticAgentExecutor:
        raise AssertionError(
            "Invalid session configuration must not initialize a provider"
        )

    monkeypatch.setattr(composition, "create_store_agent", forbidden)
    with TestClient(api_app.create_app(), raise_server_exceptions=False) as client:
        response = client.post("/api/chat", json={"message": "Hello"})
    assert response.status_code == 503
    assert value not in response.text
