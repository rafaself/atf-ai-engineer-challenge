"""Owned persistent-history boundary."""

from typing import Protocol
from uuid import UUID

from emporio_music.domain.conversations import (
    ConversationSession,
    ConversationSnapshot,
    ConversationSummary,
    ConversationTranscript,
    HistoryLimits,
)
from emporio_music.domain.identity import CustomerIdentity


class ConversationRepository(Protocol):
    """Short, synchronous local operations; append commits one complete turn."""

    def list_for(
        self, identity: CustomerIdentity | None
    ) -> tuple[ConversationSummary, ...]: ...

    def create(self, identity: CustomerIdentity | None) -> ConversationSession: ...

    def load(
        self,
        session_id: UUID,
        identity: CustomerIdentity | None,
        *,
        limits: HistoryLimits,
    ) -> ConversationSnapshot: ...

    def load_full(
        self, session_id: UUID, identity: CustomerIdentity | None
    ) -> ConversationTranscript: ...

    def delete(self, session_id: UUID, identity: CustomerIdentity | None) -> None: ...

    def append(
        self,
        session: ConversationSession,
        *,
        user_message: str,
        answer: str,
    ) -> None:
        """Atomically append or raise access or persistence error."""
        ...
