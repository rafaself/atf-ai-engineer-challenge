from pathlib import Path

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
from emporio_music_backend.api.app import create_app, get_service_factory
from emporio_music_backend.application import ChatService
from emporio_music_backend.contracts import ChatRequest, ChatResponse
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ConfigurationError,
    ProductRetrievalError,
    ProviderUnavailableError,
)
from emporio_music_backend.infrastructure.catalog_import import import_catalog
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)


class FakeService:
    async def chat(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(answer=request.message)


def test_http_contract_docs_and_dependency_override() -> None:
    app = create_app()
    app.dependency_overrides[get_service_factory] = lambda: lambda: FakeService()
    with TestClient(app) as client:
        assert client.post("/api/chat", json={"message": " Olá "}).json() == {
            "answer": "Olá"
        }
        for payload in (
            {"message": " "},
            {"message": "a" * 4001},
            {"message": 1},
            {"message": "Olá", "session_id": "unused"},
            {},
        ):
            assert client.post("/api/chat", json=payload).status_code == 422
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        assert "/api/chat" in schema["paths"]
        assert set(schema["components"]["schemas"]["ChatResponse"]["properties"]) == {
            "answer"
        }


def test_default_docs_and_validation_do_not_initialize_aws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_PROFILE", "unconfigured-project-profile")
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        assert client.get("/docs").status_code == 200
        assert client.post("/api/chat", json={"message": " "}).status_code == 422
        response = client.post("/api/chat", json={"message": "Olá"})
        assert response.status_code == 503
        assert response.json() == {"detail": "Agent service unavailable"}
        assert "unconfigured" not in response.text


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (ConfigurationError("private configuration"), 503),
        (ProviderUnavailableError("private provider body"), 503),
        (AgentTimeoutError("private timeout"), 504),
        (ProductRetrievalError("private SQL"), 500),
        (AgentExecutionError("private SDK"), 500),
        (RuntimeError("private unexpected fault"), 500),
    ],
)
def test_http_error_mapping_is_sanitized(error: Exception, status: int) -> None:
    class Service:
        async def chat(self, request: ChatRequest) -> ChatResponse:
            raise error

    with TestClient(create_app(Service()), raise_server_exceptions=False) as client:
        response = client.post("/api/chat", json={"message": "Olá"})
    assert response.status_code == status
    assert "private" not in response.text and "Traceback" not in response.text


def test_http_composes_service_agent_tool_and_real_sqlite(tmp_path: Path) -> None:
    data = Path(__file__).parents[3] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(data / "products.csv", data / "categories.csv", database)
    observed: list[object] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            return ModelResponse(
                parts=[ToolCallPart("search_products", {"product_name": "GD20"})]
            )
        observed.append(returns[-1].content)
        return ModelResponse(
            parts=[TextPart("Takamine GD20: R$ 2.199,00; 5 disponíveis.")]
        )

    agent = create_catalog_agent(
        AgentSettings(), SQLiteProductRepository(database), model=FunctionModel(model)
    )
    with TestClient(create_app(ChatService(agent))) as client:
        response = client.post("/api/chat", json={"message": "Quanto custa o GD20?"})
    assert response.status_code == 200 and "2.199,00" in response.json()["answer"]
    assert observed and isinstance(observed[0], dict)
    assert observed[0]["total_matches"] == 1
