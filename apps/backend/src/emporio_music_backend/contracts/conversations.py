"""Owned sessions, complete history and execution context."""

from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import UUID4, Field, model_validator

from emporio_music_backend.contracts.base import ContractModel, NonblankText
from emporio_music_backend.contracts.errors import (
    AuthenticationError,
    SessionAccessError,
)
from emporio_music_backend.contracts.identity import CustomerIdentity


class ConversationSession(ContractModel):
    """Server-created session metadata; its identifier does not grant access."""

    session_id: UUID4 = Field(default_factory=uuid4)
    owner: CustomerIdentity


class ConversationMessage(ContractModel):
    """Application-owned conversational text, never system/tool instructions."""

    role: Literal["user", "assistant"]
    content: NonblankText


class ExecutionContext(ContractModel):
    """Trusted invocation data kept separate from public chat input."""

    identity: CustomerIdentity | None = None
    session: ConversationSession | None = None
    history: tuple[ConversationMessage, ...] = ()

    @model_validator(mode="after")
    def validate_owned_history(self) -> Self:
        if self.session is not None:
            if self.identity is None:
                raise AuthenticationError("Trusted customer identity is required")
            if self.session.owner != self.identity:
                raise SessionAccessError("Conversation session is inaccessible")
        elif self.history:
            raise ValueError("Conversation history requires an owned session")
        if len(self.history) % 2 or any(
            message.role != ("user" if index % 2 == 0 else "assistant")
            for index, message in enumerate(self.history)
        ):
            raise ValueError("History must contain completed user/assistant turns")
        return self


class HistoryLimits(ContractModel):
    max_turns: Annotated[int, Field(strict=True, ge=1, le=20)] = 6
    max_characters: Annotated[int, Field(strict=True, ge=1, le=64000)] = 24000


class ConversationSnapshot(ContractModel):
    session: ConversationSession
    history: tuple[ConversationMessage, ...] = ()

    @model_validator(mode="after")
    def validate_history(self) -> Self:
        ExecutionContext(
            identity=self.session.owner, session=self.session, history=self.history
        )
        return self
