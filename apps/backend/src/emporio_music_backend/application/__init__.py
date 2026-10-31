"""Application service and transport-neutral substitution interface."""

from typing import Protocol

from emporio_music_backend.application.chat import ChatService as ChatService
from emporio_music_backend.contracts import ChatRequest, ChatResponse


class ChatServicePort(Protocol):
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Handle one stateless message without transport-specific objects."""
        ...
