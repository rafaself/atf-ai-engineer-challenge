"""Operational identity and bounded-result regressions for US-11."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.api.app import create_app
from emporio_music_backend.contracts.chat import ChatRequest, ChatResponse
from emporio_music_backend.contracts.conversations import ExecutionContext


def test_missing_operations_cannot_establish_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = "synthetic-order-regression-" + "a" * 32
    monkeypatch.setenv("DEMO_CUSTOMER_TOKENS_JSON", json.dumps({token: 999}))
    monkeypatch.setenv("OPERATIONS_DATABASE_PATH", str(tmp_path / "missing.sqlite3"))
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
            headers={"Authorization": "Bearer " + token},
        )
    assert response.status_code == 503
    assert not called
    assert token not in response.text


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
    answer = customer_answer(ctx, "Resposta atual")
    assert "7 pedidos" in answer and "25 itens" in answer and "99" not in answer
