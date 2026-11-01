"""US-10 regressions: authenticate before execution and ignore historical evidence."""

from uuid import UUID

from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.api.app import create_app
from emporio_music_backend.contracts import ChatRequest, ChatResponse, ExecutionContext


def test_missing_identity_rejected_before_chat_service() -> None:
    called = False

    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            nonlocal called
            called = True
            return ChatResponse(
                answer="Should not execute",
                session_id=UUID("00000000-0000-4000-8000-000000000001"),
            )

    with TestClient(create_app(Service())) as client:
        response = client.post("/api/chat", json={"message": "Private message"})
    assert response.status_code == 401
    assert not called


def test_output_notices_use_current_run_even_if_sdk_history_has_old_tools() -> None:
    ctx = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current-run",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "get_product_details", {"truncated": True, "total_matches": 99}
                    )
                ],
                run_id="old-run",
            ),
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "get_product_details", {"truncated": True, "total_matches": 12}
                    )
                ],
                run_id="current-run",
            ),
        ],
    )
    answer = customer_answer(ctx, "Resposta atual")
    assert "12" in answer and "99" not in answer
