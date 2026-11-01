from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from emporio_music_backend.api.app import create_app, get_chat_service_factory
from emporio_music_backend.contracts.chat import ChatRequest, ChatResponse
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ConfigurationError,
    ConversationPersistenceError,
    CustomerSelectionError,
    ProductRetrievalError,
    ProviderUnavailableError,
    SessionAccessError,
    SessionConflictError,
)


class FakeService:
    async def chat(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        assert context.identity is not None and context.identity.customer_id == 1
        assert context.history == () and context.session is None
        return ChatResponse(
            answer=request.message,
            session_id=UUID("00000000-0000-4000-8000-000000000001"),
        )


def test_http_contract_docs_and_dependency_override(
    demo_customer: dict[str, int],
) -> None:
    app = create_app()
    app.dependency_overrides[get_chat_service_factory] = lambda: lambda: FakeService()
    with TestClient(app) as client:
        assert client.post(
            "/api/chat", json={**demo_customer, "message": " Olá "}
        ).json() == {
            "answer": "Olá",
            "session_id": "00000000-0000-4000-8000-000000000001",
        }
        for payload in (
            {"message": " "},
            {"message": "a" * 4001},
            {"message": 1},
            {"message": "Olá", "session_id": "unused"},
            {"message": "Olá", "session_id": None},
            {"message": "Olá", "customer_id": "2"},
            {"message": "Olá", "customer_id": True},
            {"message": "Olá", "customer_id": 0},
            {"message": "Olá", "customer_id": 2**63},
            {"message": "Olá", "identity": {"customer_id": 2}},
            {"message": "Olá", "history": []},
            {"message": "Olá", "context": {"identity": {"customer_id": 2}}},
            {},
        ):
            response = client.post("/api/chat", json={**demo_customer, **payload})
            assert response.status_code == 422
            assert response.json() == {"detail": "Invalid chat request"}
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        assert "/api/chat" in schema["paths"]
        assert set(schema["components"]["schemas"]["ChatResponse"]["properties"]) == {
            "answer",
            "session_id",
        }
        request_schema = schema["components"]["schemas"]["DemoChatRequest"]
        assert request_schema["properties"]["session_id"]["type"] == "string"
        assert "session_id" not in request_schema["required"]
        assert "securitySchemes" not in schema["components"]


def test_default_docs_and_validation_do_not_initialize_aws(
    monkeypatch: pytest.MonkeyPatch, demo_customer: dict[str, int]
) -> None:
    monkeypatch.setenv("AWS_PROFILE", "unconfigured-project-profile")
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        assert client.get("/docs").status_code == 200
        assert (
            client.post("/api/chat", json={**demo_customer, "message": " "}).status_code
            == 422
        )
        response = client.post("/api/chat", json={**demo_customer, "message": "Olá"})
        assert response.status_code == 503
        assert response.json() == {"detail": "Agent service unavailable"}
        assert "unconfigured" not in response.text


@pytest.mark.parametrize(
    ("error", "status", "detail"),
    [
        (CustomerSelectionError("private customer"), 422, "Unknown demo customer"),
        (
            SessionAccessError("private session"),
            404,
            "Conversation session unavailable",
        ),
        (SessionConflictError("private state"), 409, "Conversation turn conflicts"),
        (ConversationPersistenceError("private database"), 500, "Conversation failed"),
        (ConfigurationError("private configuration"), 503, "Agent service unavailable"),
        (
            ProviderUnavailableError("private provider body"),
            503,
            "Agent service unavailable",
        ),
        (AgentTimeoutError("private timeout"), 504, "Conversation timed out"),
        (ProductRetrievalError("private SQL"), 500, "Conversation failed"),
        (AgentExecutionError("private SDK"), 500, "Conversation failed"),
        (RuntimeError("private unexpected fault"), 500, "Internal server error"),
    ],
)
def test_http_error_mapping_is_sanitized(
    error: Exception, status: int, detail: str, demo_customer: dict[str, int]
) -> None:
    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            raise error

    with TestClient(
        create_app(chat_service=Service()), raise_server_exceptions=False
    ) as client:
        response = client.post("/api/chat", json={**demo_customer, "message": "Olá"})
    assert response.status_code == status
    assert response.json() == {"detail": detail}
    assert "private" not in response.text and "Traceback" not in response.text
