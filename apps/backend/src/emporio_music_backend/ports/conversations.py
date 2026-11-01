"""Owned persistent-history boundary."""

from typing import Protocol
from uuid import UUID

from emporio_music_backend.contracts.conversations import (
    ConversationSession,
    ConversationSnapshot,
    HistoryLimits,
)
from emporio_music_backend.contracts.identity import CustomerIdentity


class ConversationRepository(Protocol):
    """Short, synchronous local operations; append commits one complete turn."""

    def create(self, identity: CustomerIdentity | None) -> ConversationSession: ...

    def load(
        self,
        session_id: UUID,
        identity: CustomerIdentity | None,
        *,
        limits: HistoryLimits,
    ) -> ConversationSnapshot: ...

    def append(
        self,
        session: ConversationSession,
        *,
        user_message: str,
        answer: str,
    ) -> None:
        """Atomically append or raise access or persistence error."""
        ...
