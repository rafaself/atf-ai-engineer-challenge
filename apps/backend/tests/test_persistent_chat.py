"""Failure and concurrency contracts around the durable completed-turn boundary."""

import asyncio
import sqlite3
from pathlib import Path
from typing import cast

import pytest

from emporio_music_backend.application import ChatService
from emporio_music_backend.contracts import (
    AgentResponse,
    ChatRequest,
    CustomerIdentity,
    ExecutionContext,
    HistoryLimits,
)
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ConversationPersistenceError,
    ProviderUnavailableError,
    SessionAccessError,
    SessionConflictError,
)
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)


def test_overlap_rejected_foreign_access_hidden_and_cancellation_recovers(
    conversations: SQLiteConversationRepository, trusted_context: ExecutionContext
) -> None:
    assert trusted_context.identity
    owner = trusted_context.identity
    session = conversations.create(owner)
    other = CustomerIdentity(customer_id=2)
    independent = conversations.create(other)
    calls = []

    async def exercise() -> None:
        entered = asyncio.Event()

        class Agent:
            async def run(
                self, request: ChatRequest, *, context: ExecutionContext
            ) -> AgentResponse:
                calls.append(request.message)
                if request.message == "hold":
                    entered.set()
                    await asyncio.Event().wait()
                return AgentResponse(answer="Saved answer")

        service = ChatService(Agent(), conversations)
        task = asyncio.create_task(
            service.chat(
                ChatRequest(message="hold", session_id=session.session_id),
                context=trusted_context,
            )
        )
        await entered.wait()
        with pytest.raises(SessionConflictError):
            await service.chat(
                ChatRequest(message="overlap", session_id=session.session_id),
                context=trusted_context,
            )
        with pytest.raises(SessionAccessError):
            await service.chat(
                ChatRequest(message="foreign", session_id=session.session_id),
                context=ExecutionContext(identity=other),
            )
        await service.chat(
            ChatRequest(message="independent", session_id=independent.session_id),
            context=ExecutionContext(identity=other),
        )
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert (
            conversations.load(
                session.session_id, owner, limits=HistoryLimits()
            ).revision
            == 0
        )
        await service.chat(
            ChatRequest(message="retry", session_id=session.session_id),
            context=trusted_context,
        )

    asyncio.run(exercise())
    assert calls == ["hold", "independent", "retry"]
    assert (
        conversations.load(session.session_id, owner, limits=HistoryLimits()).revision
        == 1
    )


@pytest.mark.parametrize("failure", ["timeout", "provider", "invalid"])
def test_execution_failures_never_complete_turns(
    failure: str,
    conversations: SQLiteConversationRepository,
    trusted_context: ExecutionContext,
) -> None:
    assert trusted_context.identity
    session = conversations.create(trusted_context.identity)

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            if failure == "timeout":
                await asyncio.Event().wait()
            if failure == "provider":
                raise ProviderUnavailableError("provider unavailable")
            return cast(AgentResponse, {"answer": " "})

    expected = {
        "timeout": AgentTimeoutError,
        "provider": ProviderUnavailableError,
        "invalid": AgentExecutionError,
    }[failure]
    service = ChatService(Agent(), conversations, timeout_seconds=0.01)
    with pytest.raises(expected):
        asyncio.run(
            service.chat(
                ChatRequest(message="Will fail", session_id=session.session_id),
                context=trusted_context,
            )
        )
    state = conversations.load(
        session.session_id, trusted_context.identity, limits=HistoryLimits()
    )
    assert state.revision == 0 and state.history == ()


def test_failed_append_is_not_success_and_retry_does_not_duplicate(
    tmp_path: Path, trusted_context: ExecutionContext
) -> None:
    path = tmp_path / "conversation.sqlite3"
    repository = SQLiteConversationRepository(path)
    assert trusted_context.identity
    session = repository.create(trusted_context.identity)

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            return AgentResponse(answer="Valid answer")

    service = ChatService(Agent(), repository)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TRIGGER fail_save BEFORE INSERT ON turns BEGIN SELECT RAISE(ABORT, 'simulated failure'); END"
        )
    request = ChatRequest(message="Retry me", session_id=session.session_id)
    with pytest.raises(ConversationPersistenceError):
        asyncio.run(service.chat(request, context=trusted_context))
    assert (
        repository.load(
            session.session_id, trusted_context.identity, limits=HistoryLimits()
        ).revision
        == 0
    )
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER fail_save")
    response = asyncio.run(service.chat(request, context=trusted_context))
    assert response.session_id == session.session_id
    state = repository.load(
        session.session_id, trusted_context.identity, limits=HistoryLimits()
    )
    assert state.revision == 1 and [m.content for m in state.history] == [
        "Retry me",
        "Valid answer",
    ]


def test_separate_service_instances_detect_stale_history(
    conversations: SQLiteConversationRepository, trusted_context: ExecutionContext
) -> None:
    assert trusted_context.identity
    session = conversations.create(trusted_context.identity)

    async def exercise() -> None:
        entered = 0
        ready = asyncio.Event()

        class Agent:
            async def run(
                self, request: ChatRequest, *, context: ExecutionContext
            ) -> AgentResponse:
                nonlocal entered
                entered += 1
                if entered == 2:
                    ready.set()
                await ready.wait()
                return AgentResponse(answer="Only one commit wins")

        services = [
            ChatService(Agent(), conversations),
            ChatService(
                Agent(), SQLiteConversationRepository(conversations.database_path)
            ),
        ]
        outcomes = await asyncio.gather(
            *(
                service.chat(
                    ChatRequest(message="Race", session_id=session.session_id),
                    context=trusted_context,
                )
                for service in services
            ),
            return_exceptions=True,
        )
        assert (
            sum(isinstance(outcome, SessionConflictError) for outcome in outcomes) == 1
        )
        assert sum(not isinstance(outcome, BaseException) for outcome in outcomes) == 1

    asyncio.run(exercise())
    state = conversations.load(
        session.session_id, trusted_context.identity, limits=HistoryLimits()
    )
    assert state.revision == 1 and len(state.history) == 2
