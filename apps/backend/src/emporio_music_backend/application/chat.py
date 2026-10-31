"""Transport-independent execution with caller-supplied, application-owned context."""

import asyncio
import math

from emporio_music_backend.contracts import ChatRequest, ChatResponse, ExecutionContext
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
)
from emporio_music_backend.ports import AgentExecutor


class ChatService:
    """Own the complete conversation deadline; adapters own individual request limits."""

    def __init__(self, agent: AgentExecutor, *, timeout_seconds: float = 60) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ConfigurationError("Chat timeout must be positive and finite")
        self._agent = agent
        self._timeout_seconds = timeout_seconds

    async def chat(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        # Keep contract failures distinct from execution faults.
        validated = ChatRequest.model_validate(request)
        validated_context = ExecutionContext.model_validate(context)
        try:
            async with asyncio.timeout(self._timeout_seconds):
                response = await self._agent.run(validated, context=validated_context)
                return ChatResponse.model_validate(response)
        except ApplicationError:
            raise
        except TimeoutError as exc:
            raise AgentTimeoutError("Conversation execution timed out") from exc
        except Exception as exc:
            raise AgentExecutionError("Conversation execution failed") from exc
