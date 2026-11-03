"""Provider-backed SSE orchestration preserves complete-turn persistence."""

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing
from pathlib import Path
from typing import Any
from uuid import UUID

import emporio_music_api.app as api_app
import pytest
from emporio_music.application.chat import ChatService
from emporio_music.domain.chat import AgentResponse, ChatRequest, ChatResponse
from emporio_music.domain.conversations import (
    ConversationMessage,
    ExecutionContext,
    HistoryLimits,
)
from emporio_music.domain.errors import (
    AgentTimeoutError,
    ProviderUnavailableError,
    SessionConflictError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.conversations import SQLiteConversationRepository
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.ports.agent import AgentStreamEvent, AgentTextDelta
from emporio_music.ports.chat import ChatStreamDelta
from emporio_music_api.app import create_app
from fastapi.testclient import TestClient


async def _agent_response(
    _request: ChatRequest, *, context: ExecutionContext
) -> AgentResponse:
    return AgentResponse(answer="Resposta validada")


async def _run_inline(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return function(*args, **kwargs)


def test_stream_commits_exact_validated_answer_before_done(
    conversations: SQLiteConversationRepository,
) -> None:
    identity = CustomerIdentity(customer_id=1)
    session = conversations.create(identity)

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            return await _agent_response(request, context=context)

        async def stream(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AsyncGenerator[AgentStreamEvent, None]:
            yield AgentTextDelta(text="Rascunho")
            yield AgentResponse(answer="Resposta final com validação")

    service = ChatService(Agent(), conversations)

    async def exercise() -> None:
        events = service.stream(
            ChatRequest(message="Olá", session_id=session.session_id),
            context=ExecutionContext(identity=identity),
        )
        async with aclosing(events):
            delta = await anext(events)
            assert delta == ChatStreamDelta(text="Rascunho")
            assert (
                conversations.load(
                    session.session_id, identity, limits=HistoryLimits()
                ).history
                == ()
            )

            done = await anext(events)
            assert done == ChatResponse(
                answer="Resposta final com validação", session_id=session.session_id
            )
            assert [
                message.content
                for message in conversations.load(
                    session.session_id, identity, limits=HistoryLimits()
                ).history
            ] == ["Olá", "Resposta final com validação"]

    asyncio.run(exercise())


def test_stream_uses_bounded_history_from_the_owned_session(
    conversations: SQLiteConversationRepository,
) -> None:
    identity = CustomerIdentity(customer_id=1)
    session = conversations.create(identity)
    for user_message, answer in (
        ("old question", "old answer"),
        ("recent", "recent answer"),
    ):
        conversations.append(session, user_message=user_message, answer=answer)
    received_history: list[ConversationMessage] = []

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            return AgentResponse(answer="done")

        async def stream(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AsyncGenerator[AgentStreamEvent, None]:
            received_history.extend(context.history)
            yield AgentResponse(answer="done")

    service = ChatService(
        Agent(), conversations, history_limits=HistoryLimits(max_turns=1)
    )
    events = service.stream(
        ChatRequest(message="current", session_id=session.session_id),
        context=ExecutionContext(identity=identity),
    )

    async def exercise() -> None:
        async with aclosing(events):
            response = await anext(events)
            assert isinstance(response, ChatResponse)

    asyncio.run(exercise())
    assert [message.content for message in received_history] == [
        "recent",
        "recent answer",
    ]


def test_stream_failure_after_deltas_never_persists_a_partial_pair(
    conversations: SQLiteConversationRepository,
) -> None:
    identity = CustomerIdentity(customer_id=1)
    session = conversations.create(identity)

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            return AgentResponse(answer="unused")

        async def stream(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AsyncGenerator[AgentStreamEvent, None]:
            yield AgentTextDelta(text="Visible provisional text")
            raise ProviderUnavailableError("private provider details")

    events = ChatService(Agent(), conversations).stream(
        ChatRequest(message="Olá", session_id=session.session_id),
        context=ExecutionContext(identity=identity),
    )

    async def exercise() -> None:
        async with aclosing(events):
            assert await anext(events) == ChatStreamDelta(
                text="Visible provisional text"
            )
            with pytest.raises(ProviderUnavailableError):
                await anext(events)

    asyncio.run(exercise())
    assert (
        conversations.load(session.session_id, identity, limits=HistoryLimits()).history
        == ()
    )


def test_stream_timeout_and_cancellation_release_the_session_and_save_nothing(
    conversations: SQLiteConversationRepository,
) -> None:
    identity = CustomerIdentity(customer_id=1)
    session = conversations.create(identity)

    class TimeoutAgent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            return AgentResponse(answer="unused")

        async def stream(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AsyncGenerator[AgentStreamEvent, None]:
            yield AgentTextDelta(text="timed-out draft")
            await asyncio.Event().wait()

    timeout_service = ChatService(TimeoutAgent(), conversations, timeout_seconds=0.02)

    async def exercise() -> None:
        request = ChatRequest(message="Olá", session_id=session.session_id)
        first = timeout_service.stream(
            request, context=ExecutionContext(identity=identity)
        )
        with pytest.raises(AgentTimeoutError):
            async with aclosing(first):
                assert await anext(first) == ChatStreamDelta(text="timed-out draft")
                await anext(first)
        assert (
            conversations.load(
                session.session_id, identity, limits=HistoryLimits()
            ).history
            == ()
        )

    asyncio.run(exercise())

    cancelled: list[bool] = []
    calls = 0

    class CancellationAgent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            return AgentResponse(answer="retry succeeded")

        async def stream(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AsyncGenerator[AgentStreamEvent, None]:
            nonlocal calls
            calls += 1
            if calls == 1:
                try:
                    yield AgentTextDelta(text="cancelled draft")
                    await asyncio.Event().wait()
                finally:
                    cancelled.append(True)
            else:
                yield AgentResponse(answer="retry succeeded")

    service = ChatService(CancellationAgent(), conversations)

    async def cancel_and_retry() -> None:
        request = ChatRequest(message="Olá", session_id=session.session_id)

        task_entered = asyncio.Event()

        async def consume_until_cancelled() -> None:
            events = service.stream(
                request, context=ExecutionContext(identity=identity)
            )
            async with aclosing(events):
                assert await anext(events) == ChatStreamDelta(text="cancelled draft")
                task_entered.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(consume_until_cancelled())
        await task_entered.wait()
        conflict = service.stream(request, context=ExecutionContext(identity=identity))
        async with aclosing(conflict):
            with pytest.raises(SessionConflictError):
                await anext(conflict)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        retry = service.stream(request, context=ExecutionContext(identity=identity))
        async with aclosing(retry):
            response = await anext(retry)
            assert response == ChatResponse(
                answer="retry succeeded", session_id=session.session_id
            )

    asyncio.run(cancel_and_retry())
    assert cancelled == [True]
    assert [
        message.content
        for message in conversations.load(
            session.session_id, identity, limits=HistoryLimits()
        ).history
    ] == ["Olá", "retry succeeded"]


def test_http_stream_emits_deltas_then_authoritative_done_without_changing_chat(
    operational_database: Path,
    fixed_demo_identity: CustomerIdentity,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = UUID("00000000-0000-4000-8000-000000000001")
    identities: list[CustomerIdentity | None] = []

    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            identities.append(context.identity)
            return ChatResponse(answer=request.message, session_id=session_id)

        async def stream(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AsyncGenerator[ChatStreamDelta | ChatResponse, None]:
            identities.append(context.identity)
            yield ChatStreamDelta(text="Olá ")
            yield ChatStreamDelta(text="mundo")
            yield ChatResponse(answer="Olá mundo final", session_id=session_id)

    app = create_app(chat_service=Service())
    monkeypatch.setattr(api_app, "run_in_threadpool", _run_inline)
    monkeypatch.setattr(
        api_app,
        "create_order_repository",
        lambda: SQLiteOrderRepository(operational_database),
    )
    with TestClient(app) as client:
        normal = client.post("/api/chat", json={"message": "Olá"})
        stream = client.post("/api/chat/stream", json={"message": "Olá"})
        forged = client.post(
            "/api/chat/stream", json={"message": "Olá", "customer_id": 2}
        )

    assert normal.status_code == 200
    assert normal.json() == ChatResponse(
        answer="Olá", session_id=session_id
    ).model_dump(mode="json")
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    body = stream.text
    assert [line for line in body.splitlines() if line.startswith("event:")] == [
        "event: delta",
        "event: delta",
        "event: done",
    ]
    assert 'data: {"answer":"Olá mundo final","session_id":"' in body
    assert forged.status_code == 422
    assert forged.json() == {"detail": "Invalid chat request"}
    assert identities == [fixed_demo_identity, fixed_demo_identity]


def test_http_stream_sanitizes_service_failures_into_error_events(
    operational_database: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Service:
        async def chat(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> ChatResponse:
            raise AssertionError("unused")

        async def stream(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AsyncGenerator[ChatStreamDelta | ChatResponse, None]:
            if False:
                yield ChatStreamDelta(text="unreachable")
            raise SessionConflictError("private database and customer details")

    app = create_app(chat_service=Service())
    monkeypatch.setattr(api_app, "run_in_threadpool", _run_inline)
    monkeypatch.setattr(
        api_app,
        "create_order_repository",
        lambda: SQLiteOrderRepository(operational_database),
    )
    with TestClient(app) as client:
        response = client.post("/api/chat/stream", json={"message": "Olá"})

    body = response.text
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: error\n" in body
    assert 'data: {"message":"Conversation turn conflicts"}' in body
    assert "private" not in body
    assert json.loads(body.split("data: ", 1)[1].splitlines()[0]) == {
        "message": "Conversation turn conflicts"
    }
