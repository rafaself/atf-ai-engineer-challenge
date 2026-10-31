"""Application entry-point contract; concrete orchestration belongs to US-06."""

from typing import Protocol

from emporio_music_backend.contracts import ChatRequest, ChatResponse


class ChatService(Protocol):
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Handle one stateless message without transport-specific objects."""
        ...
