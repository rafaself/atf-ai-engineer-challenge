"""Transport-neutral chat request and response values."""

from typing import Annotated

from pydantic import UUID4, Field

from emporio_music_backend.contracts.base import ContractModel, NonblankText


class ChatRequest(ContractModel):
    message: Annotated[NonblankText, Field(max_length=4000)]
    session_id: UUID4 | None = None


class AgentResponse(ContractModel):
    answer: NonblankText


class ChatResponse(AgentResponse):
    session_id: UUID4
