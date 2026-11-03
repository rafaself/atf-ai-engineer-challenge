"""US-10 regressions: fixed identity at the boundary and current evidence only."""

from uuid import UUID

from emporio_music.agent.output import customer_answer
from emporio_music.domain.chat import ChatRequest, ChatResponse
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.identity import CustomerIdentity
from emporio_music_api.app import create_app
from fastapi.testclient import TestClient
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from tests._support import run_async


def test_http_omission_uses_fixed_identity_without_customer_metadata(
    fixed_demo_identity: CustomerIdentity,
) -> None:
    called = False

    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            nonlocal called
            called = True
            assert context.identity == CustomerIdentity(customer_id=1)
            assert request.model_dump(exclude_none=True) == {"message": "Olá"}
            return ChatResponse(
                answer="Resposta",
                session_id=UUID("00000000-0000-4000-8000-000000000001"),
            )

    with TestClient(create_app(Service())) as client:
        response = client.post("/api/chat", json={"message": "Olá"})
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
    answer = run_async(customer_answer(ctx, "Resposta atual"))
    assert "12" in answer and "99" not in answer
