"""Owned persistent conversations behind transport-independent application ports."""

import asyncio
import math
from uuid import UUID

from emporio_music_backend.contracts.chat import (
    AgentResponse,
    ChatRequest,
    ChatResponse,
)
from emporio_music_backend.contracts.conversations import (
    ExecutionContext,
    HistoryLimits,
)
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    SessionConflictError,
)
from emporio_music_backend.ports.agent import AgentExecutor
from emporio_music_backend.ports.conversations import ConversationRepository


class ChatService:
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
        session_id = validated.session_id
        held: UUID | None = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._timeout_seconds
        try:
            async with asyncio.timeout_at(deadline):
                if session_id is None:
                    session_id = self._conversations.create(identity).session_id
                # Ownership is checked before consulting active state, so a foreign
                # session gets the same response whether idle, active, or nonexistent.
                snapshot = self._conversations.load(
                    session_id, identity, limits=self._history_limits
                )
                if session_id in self._active:
                    raise SessionConflictError("Conversation turn conflicts")
                self._active.add(session_id)
                held = session_id
                execution = ExecutionContext(
                    identity=identity,
                    session=snapshot.session,
                    history=snapshot.history,
                )
                if loop.time() >= deadline:
                    raise TimeoutError
                result = AgentResponse.model_validate(
                    await self._agent.run(validated, context=execution)
                )
                # Deliver pending cancellation before beginning the non-awaiting commit.
                await asyncio.sleep(0)
                if loop.time() >= deadline:
                    raise TimeoutError
                # Short synchronous commit: timeout=0 in SQLite, no worker can append
                # later after async cancellation. No transaction spans the model call.
                self._conversations.append(
                    snapshot.session,
                    user_message=validated.message,
                    answer=result.answer,
                )
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
