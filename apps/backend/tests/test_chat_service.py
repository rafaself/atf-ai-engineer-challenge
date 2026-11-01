import asyncio
from typing import cast

import pytest
from pydantic import ValidationError

from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.contracts.chat import AgentResponse, ChatRequest
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    ProductRetrievalError,
    ProviderUnavailableError,
)
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.ports.chat import ChatServicePort


def test_service_runs_without_http_and_keeps_no_match_as_success(
    conversations: SQLiteConversationRepository, trusted_context: ExecutionContext
) -> None:
    requests: list[ChatRequest] = []

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            requests.append(request)
            return AgentResponse(answer="Nenhum produto encontrado para os filtros.")

    service: ChatServicePort = ChatService(Agent(), conversations)
    request = ChatRequest(message="Buscar produto inexistente")
    response = asyncio.run(service.chat(request, context=trusted_context))
    assert response.answer == "Nenhum produto encontrado para os filtros."
    assert requests == [request]
    with pytest.raises(ValidationError):
        asyncio.run(
            service.chat(cast(ChatRequest, {"message": " "}), context=trusted_context)
        )
    assert requests == [request]


@pytest.mark.parametrize(
    "failure",
    [
        ProviderUnavailableError("provider detail"),
        ProductRetrievalError("catalog detail"),
        ConfigurationError("configuration detail"),
    ],
)
def test_service_preserves_typed_failures(
    failure: ApplicationError,
    conversations: SQLiteConversationRepository,
    trusted_context: ExecutionContext,
) -> None:
    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            raise failure

    with pytest.raises(type(failure)) as error:
        asyncio.run(
            ChatService(Agent(), conversations).chat(
                ChatRequest(message="Olá"), context=trusted_context
            )
        )
    assert error.value is failure


def test_service_wraps_unexpected_failure_without_leaking_details(
    conversations: SQLiteConversationRepository, trusted_context: ExecutionContext
) -> None:
    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            raise RuntimeError("private SDK body")

    with pytest.raises(AgentExecutionError) as error:
        asyncio.run(
            ChatService(Agent(), conversations).chat(
                ChatRequest(message="Olá"), context=trusted_context
            )
        )
    assert str(error.value) == "Conversation execution failed"
    assert isinstance(error.value.__cause__, RuntimeError)


def test_deadline_cancels_execution_and_caller_cancellation_propagates(
    conversations: SQLiteConversationRepository, trusted_context: ExecutionContext
) -> None:
    cancelled: list[bool] = []

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            try:
                await asyncio.Event().wait()
                raise AssertionError("unreachable")
            finally:
                cancelled.append(True)

    async def exercise() -> None:
        with pytest.raises(AgentTimeoutError):
            await ChatService(Agent(), conversations, timeout_seconds=0.01).chat(
                ChatRequest(message="Olá"), context=trusted_context
            )
        task = asyncio.create_task(
            ChatService(Agent(), conversations).chat(
                ChatRequest(message="Olá"), context=trusted_context
            )
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    assert cancelled == [True, True]
    with pytest.raises(ConfigurationError):
        ChatService(Agent(), conversations, timeout_seconds=float("inf"))
