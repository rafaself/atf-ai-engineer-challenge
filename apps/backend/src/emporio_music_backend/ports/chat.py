"""Transport-independent chat-service boundary."""

from typing import Protocol

from emporio_music_backend.contracts.chat import ChatRequest, ChatResponse
from emporio_music_backend.contracts.conversations import ExecutionContext


class ChatServicePort(Protocol):
    async def chat(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        """Handle a message with trusted context, without transport-specific objects."""
        ...
