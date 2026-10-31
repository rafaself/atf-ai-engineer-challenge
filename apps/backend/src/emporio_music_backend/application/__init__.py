"""Application service and transport-neutral substitution interface."""

from typing import Protocol

from emporio_music_backend.application.chat import ChatService as ChatService
from emporio_music_backend.contracts import ChatRequest, ChatResponse, ExecutionContext


class ChatServicePort(Protocol):
    async def chat(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        """Handle a message with trusted context, without transport-specific objects."""
        ...
