"""Provider-independent agent execution boundary."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Protocol

from emporio_music.domain.chat import AgentResponse, ChatRequest
from emporio_music.domain.conversations import ExecutionContext


class AgentExecutor(Protocol):
    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        """Execute with trusted, application-owned context; translate provider faults."""
        ...


@dataclass(frozen=True)
class AgentTextDelta:
    """A provisional user-facing text fragment from a running agent."""

    text: str


type AgentStreamEvent = AgentTextDelta | AgentResponse


class StreamingAgentExecutor(AgentExecutor, Protocol):
    """Agent execution port that also exposes provisional text and final output."""

    def stream(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AsyncGenerator[AgentStreamEvent, None]:
        """Run to completion while yielding user-facing text fragments."""
        ...
