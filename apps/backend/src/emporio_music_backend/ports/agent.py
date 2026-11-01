"""Provider-independent agent execution boundary."""

from typing import Protocol

from emporio_music_backend.contracts.chat import AgentResponse, ChatRequest
from emporio_music_backend.contracts.conversations import ExecutionContext


class AgentExecutor(Protocol):
    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        """Execute with trusted, application-owned context; translate provider faults."""
        ...
