import asyncio
from typing import cast

import pytest
from pydantic import ValidationError

from emporio_music_backend.application import ChatService, ChatServicePort
from emporio_music_backend.contracts import ChatRequest, ChatResponse, ExecutionContext
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    ProductRetrievalError,
    ProviderUnavailableError,
)


def test_service_runs_without_http_and_keeps_no_match_as_success() -> None:
    requests: list[ChatRequest] = []

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            requests.append(request)
            return ChatResponse(answer="Nenhum produto encontrado para os filtros.")

    service: ChatServicePort = ChatService(Agent())
    request = ChatRequest(message="Buscar produto inexistente")
    response = asyncio.run(service.chat(request, context=ExecutionContext()))
    assert response.answer == "Nenhum produto encontrado para os filtros."
    assert requests == [request]
    with pytest.raises(ValidationError):
        asyncio.run(
            service.chat(
                cast(ChatRequest, {"message": " "}), context=ExecutionContext()
            )
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
def test_service_preserves_typed_failures(failure: ApplicationError) -> None:
    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            raise failure

    with pytest.raises(type(failure)) as error:
        asyncio.run(
            ChatService(Agent()).chat(
                ChatRequest(message="Olá"), context=ExecutionContext()
            )
        )
    assert error.value is failure


def test_service_wraps_unexpected_failure_without_leaking_details() -> None:
    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            raise RuntimeError("private SDK body")

    with pytest.raises(AgentExecutionError) as error:
        asyncio.run(
            ChatService(Agent()).chat(
                ChatRequest(message="Olá"), context=ExecutionContext()
            )
        )
    assert str(error.value) == "Conversation execution failed"
    assert isinstance(error.value.__cause__, RuntimeError)


def test_deadline_cancels_execution_and_caller_cancellation_propagates() -> None:
    cancelled: list[bool] = []

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            try:
                await asyncio.Event().wait()
                raise AssertionError("unreachable")
            finally:
                cancelled.append(True)

    async def exercise() -> None:
        with pytest.raises(AgentTimeoutError):
            await ChatService(Agent(), timeout_seconds=0.01).chat(
                ChatRequest(message="Olá"), context=ExecutionContext()
            )
        task = asyncio.create_task(
            ChatService(Agent()).chat(
                ChatRequest(message="Olá"), context=ExecutionContext()
            )
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    assert cancelled == [True, True]
    with pytest.raises(ConfigurationError):
        ChatService(Agent(), timeout_seconds=float("inf"))
