"""US-10 regressions: guest context at the boundary and ignore historical evidence."""

from uuid import UUID

from emporio_music.agent.output import customer_answer
from emporio_music.domain.chat import ChatRequest, ChatResponse
from emporio_music.domain.conversations import ExecutionContext
from emporio_music_api.app import create_app
from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage


def test_guest_reaches_chat_service_without_customer_metadata() -> None:
    called = False

    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            nonlocal called
            called = True
            assert context.identity is None
            assert request.model_dump(exclude_none=True) == {"message": "Olá"}
            return ChatResponse(
                answer="Resposta",
                session_id=UUID("00000000-0000-4000-8000-000000000001"),
            )

    with TestClient(create_app(Service())) as client:
        response = client.post(
            "/api/chat", json={"message": "Olá", "customer_id": None}
        )
    assert response.status_code == 200
    assert called


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
                        "find_product_by_name", {"truncated": True, "total_matches": 99}
                    )
                ],
                run_id="old-run",
            ),
            ModelRequest(
                parts=[
                    ToolReturnPart(
                        "find_product_by_name", {"truncated": True, "total_matches": 12}
                    )
                ],
                run_id="current-run",
            ),
        ],
    )
    answer = customer_answer(ctx, "Resposta atual")
    assert "12" in answer and "99" not in answer
