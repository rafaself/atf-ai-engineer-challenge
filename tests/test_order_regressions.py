"""Operational identity and bounded-result regressions for US-11."""

from pathlib import Path
from uuid import uuid4

import pytest
from emporio_music import paths
from emporio_music.agent.output import customer_answer
from emporio_music.domain.chat import ChatRequest, ChatResponse
from emporio_music.domain.conversations import ExecutionContext
from emporio_music_api.app import create_app
from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from tests._support import run_async


def test_missing_operations_cannot_resolve_fixed_demo_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paths, "OPERATIONS_DATABASE_PATH", tmp_path / "missing.sqlite3")
    called = []

    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            called.append(True)
            return ChatResponse(answer="Must not execute", session_id=uuid4())

    with TestClient(create_app(Service())) as client:
        response = client.post(
            "/api/chat",
            json={"message": "My orders"},
        )
    assert response.status_code == 503
    assert not called
    assert "sqlite3" not in response.text


def test_order_notices_use_only_current_evidence() -> None:
    ctx = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "list_my_orders", {"total_matches": 99, "truncated": True}
                    )
                ],
                run_id="old",
            ),
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "list_my_orders", {"total_matches": 7, "truncated": True}
                    )
                ],
                run_id="current",
            ),
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "get_my_order",
                        {"order": {"total_items": 25, "items_truncated": True}},
                    )
                ],
                run_id="current",
            ),
        ],
    )
    answer = run_async(customer_answer(ctx, "Resposta atual"))
    assert "7 pedidos" in answer and "25 itens" in answer and "99" not in answer
