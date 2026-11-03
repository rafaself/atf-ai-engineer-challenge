"""Transport-independent chat-service boundary."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Protocol

from emporio_music.domain.chat import ChatRequest, ChatResponse
from emporio_music.domain.conversations import ExecutionContext


class ChatServicePort(Protocol):
    async def chat(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        """Handle a message with trusted context, without transport-specific objects."""
        ...


@dataclass(frozen=True)
class ChatStreamDelta:
    """A provisional text fragment from a chat turn."""

    text: str


type ChatStreamEvent = ChatStreamDelta | ChatResponse


class StreamingChatServicePort(ChatServicePort, Protocol):
    """Chat-service boundary for complete turns that expose provisional text."""

    def stream(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        """Yield deltas, then the authoritative committed response."""
        ...
