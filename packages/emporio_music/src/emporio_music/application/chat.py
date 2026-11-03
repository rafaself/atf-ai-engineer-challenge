"""Owned persistent conversations behind transport-independent application ports."""

import asyncio
import math
from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import cast
from uuid import UUID

from emporio_music.domain.chat import (
    AgentResponse,
    ChatRequest,
    ChatResponse,
)
from emporio_music.domain.conversations import (
    ConversationSnapshot,
    ExecutionContext,
    HistoryLimits,
)
from emporio_music.domain.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    SessionConflictError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.ports.agent import (
    AgentExecutor,
    AgentTextDelta,
    StreamingAgentExecutor,
)
from emporio_music.ports.chat import (
    ChatStreamDelta,
    ChatStreamEvent,
    StreamingChatServicePort,
)
from emporio_music.ports.conversations import ConversationRepository


class ChatService(StreamingChatServicePort):
    """Run one turn and commit it before returning success; retain no history cache."""

    def __init__(
        self,
        agent: AgentExecutor,
        conversations: ConversationRepository,
        *,
        timeout_seconds: float = 60,
        history_limits: HistoryLimits | None = None,
    ) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ConfigurationError("Chat timeout must be positive and finite")
        self._agent = agent
        self._conversations = conversations
        self._timeout_seconds = timeout_seconds
        self._history_limits = HistoryLimits.model_validate(
            history_limits or HistoryLimits()
        )
        # Only active IDs are retained. Access is synchronous on the local server loop;
        # The demo supports one service instance/process; no cross-instance coordinator.
        self._active: set[UUID] = set()

    async def chat(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        validated = ChatRequest.model_validate(request)
        trusted = ExecutionContext.model_validate(context)
        if trusted.session is not None or trusted.history:
            raise ValueError("ChatService loads session history from its repository")
        identity = trusted.identity
        held: UUID | None = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout_seconds
        try:
            async with asyncio.timeout_at(deadline):
                session_id, snapshot, execution = self._begin_turn(validated, identity)
                held = session_id
                if loop.time() >= deadline:
                    raise TimeoutError
                result = AgentResponse.model_validate(
                    await self._agent.run(validated, context=execution)
                )
                # Deliver pending cancellation before beginning the non-awaiting commit.
                await asyncio.sleep(0)
                if loop.time() >= deadline:
                    raise TimeoutError
                self._commit_turn(snapshot, validated, result)
                return ChatResponse(answer=result.answer, session_id=session_id)
        except ApplicationError:
            raise
        except TimeoutError as exc:
            raise AgentTimeoutError("Conversation execution timed out") from exc
        except Exception as exc:
            raise AgentExecutionError("Conversation execution failed") from exc
        finally:
            if held is not None:
                self._active.remove(held)

    async def stream(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """Stream provisional text, then commit and yield the validated response."""
        validated = ChatRequest.model_validate(request)
        trusted = ExecutionContext.model_validate(context)
        if trusted.session is not None or trusted.history:
            raise ValueError("ChatService loads session history from its repository")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout_seconds
        held: UUID | None = None
        try:
            async with asyncio.timeout_at(deadline):
                session_id, snapshot, execution = self._begin_turn(
                    validated, trusted.identity
                )
                held = session_id
                if loop.time() >= deadline:
                    raise TimeoutError
                final: AgentResponse | None = None
                agent_events = cast(StreamingAgentExecutor, self._agent).stream(
                    validated, context=execution
                )
                async with aclosing(agent_events) as events:
                    async for event in events:
                        if isinstance(event, AgentTextDelta):
                            if event.text:
                                yield ChatStreamDelta(text=event.text)
                        else:
                            if final is not None:
                                raise AgentExecutionError(
                                    "Agent stream produced multiple answers"
                                )
                            final = AgentResponse.model_validate(event)
                if final is None:
                    raise AgentExecutionError("Agent stream did not complete")
                # Give pending cancellation a chance to run before the synchronous
                # transaction. The final event can only follow this single commit.
                await asyncio.sleep(0)
                if loop.time() >= deadline:
                    raise TimeoutError
                self._commit_turn(snapshot, validated, final)
                yield ChatResponse(answer=final.answer, session_id=session_id)
        except ApplicationError:
            raise
        except TimeoutError as exc:
            raise AgentTimeoutError("Conversation execution timed out") from exc
        except Exception as exc:
            raise AgentExecutionError("Conversation execution failed") from exc
        finally:
            if held is not None:
                self._active.remove(held)

    def _begin_turn(
        self, request: ChatRequest, identity: CustomerIdentity | None
    ) -> tuple[UUID, ConversationSnapshot, ExecutionContext]:
        session_id = request.session_id
        if session_id is None:
            session_id = self._conversations.create(identity).session_id
        # Ownership is checked before consulting active state, so a foreign
        # session gets the same response whether idle, active, or nonexistent.
        snapshot = self._conversations.load(
            session_id, identity, limits=self._history_limits
        )
        if session_id in self._active:
            raise SessionConflictError("Conversation turn conflicts")
        execution = ExecutionContext(
            identity=identity,
            session=snapshot.session,
            history=snapshot.history,
        )
        self._active.add(session_id)
        return session_id, snapshot, execution

    def _commit_turn(
        self,
        snapshot: ConversationSnapshot,
        request: ChatRequest,
        response: AgentResponse,
    ) -> None:
        # Short synchronous commit: timeout=0 in SQLite, no worker can append
        # later after async cancellation. No transaction spans the model call.
        self._conversations.append(
            snapshot.session,
            user_message=request.message,
            answer=response.answer,
        )
