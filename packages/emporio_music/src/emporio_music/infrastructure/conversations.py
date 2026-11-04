"""Owned local conversation storage, separate from replaceable source snapshots."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import (
    ConversationMessage,
    ConversationSession,
    ConversationSnapshot,
    ConversationSummary,
    ConversationTranscript,
    ExecutionContext,
    HistoryLimits,
)
from emporio_music.domain.errors import (
    ConversationPersistenceError,
    SessionAccessError,
)
from emporio_music.domain.identity import CustomerIdentity

_APPLICATION_ID = 0x454D434F
_SCHEMA_VERSION = 2


class SQLiteConversationRepository:
    """Fail-fast SQLite operations; no connection or transaction spans model work."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(
                    self.database_path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600
                )
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
            with closing(self._connect(verify=False)) as connection:
                connection.execute("BEGIN IMMEDIATE")
                application_id = connection.execute("PRAGMA application_id").fetchone()[
                    0
                ]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                tables = connection.execute("SELECT name FROM sqlite_master").fetchall()
                if application_id == 0 and version == 0 and not tables:
                    connection.execute(
                        "CREATE TABLE sessions (session_id TEXT PRIMARY KEY, "
                        "customer_id INTEGER CHECK(customer_id > 0))"
                    )
                    connection.execute(
                        "CREATE TABLE turns (session_id TEXT NOT NULL REFERENCES sessions(session_id), "
                        "sequence INTEGER NOT NULL CHECK(sequence > 0), "
                        "user_message TEXT NOT NULL CHECK(length(user_message) > 0), "
                        "answer TEXT NOT NULL CHECK(length(answer) > 0), "
                        "PRIMARY KEY (session_id, sequence))"
                    )
                    connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
                    connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
                elif application_id != _APPLICATION_ID or version != _SCHEMA_VERSION:
                    raise ConversationPersistenceError(
                        "Conversation database is incompatible"
                    )
                connection.commit()
            self.database_path.chmod(0o600)
        except (OSError, sqlite3.Error) as exc:
            raise ConversationPersistenceError(
                "Conversation storage is unavailable"
            ) from exc

    def _connect(self, *, verify: bool = True) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path.as_uri() + "?mode=rw",
            uri=True,
            timeout=0,
            isolation_level=None,
        )
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            if verify and (
                connection.execute("PRAGMA application_id").fetchone()[0]
                != _APPLICATION_ID
                or connection.execute("PRAGMA user_version").fetchone()[0]
                != _SCHEMA_VERSION
            ):
                raise ConversationPersistenceError(
                    "Conversation database is incompatible"
                )
        except Exception:
            connection.close()
            raise
        return connection

    def create(self, identity: CustomerIdentity | None) -> ConversationSession:
        if identity is not None:
            identity = CustomerIdentity.model_validate(identity)
        session = ConversationSession(owner=identity)
        try:
            with closing(self._connect()) as connection:
                connection.execute(
                    "INSERT INTO sessions (session_id, customer_id) VALUES (?, ?)",
                    (
                        str(session.session_id),
                        identity.customer_id if identity else None,
                    ),
                )
        except sqlite3.Error as exc:
            raise ConversationPersistenceError(
                "Conversation session could not be created"
            ) from exc
        return session

    def list_for(
        self, identity: CustomerIdentity | None
    ) -> tuple[ConversationSummary, ...]:
        """List completed sessions by most recent persisted turn."""
        if identity is not None:
            identity = CustomerIdentity.model_validate(identity)
        try:
            with closing(self._connect()) as connection:
                rows = connection.execute(
                    "SELECT s.session_id, "
                    "(SELECT t.user_message FROM turns AS t "
                    " WHERE t.session_id = s.session_id ORDER BY t.sequence LIMIT 1) "
                    "FROM sessions AS s "
                    "WHERE s.customer_id IS ? "
                    "AND EXISTS (SELECT 1 FROM turns AS t "
                    " WHERE t.session_id = s.session_id) "
                    "ORDER BY (SELECT max(t.rowid) FROM turns AS t "
                    " WHERE t.session_id = s.session_id) DESC",
                    (identity.customer_id if identity else None,),
                ).fetchall()
                return tuple(
                    ConversationSummary(
                        session_id=UUID(session_id),
                        title=title,
                    )
                    for session_id, title in rows
                )
        except (sqlite3.Error, ValidationError, ValueError) as exc:
            raise ConversationPersistenceError(
                "Conversation history could not be listed"
            ) from exc

    def load(
        self,
        session_id: UUID,
        identity: CustomerIdentity | None,
        *,
        limits: HistoryLimits,
    ) -> ConversationSnapshot:
        if identity is not None:
            identity = CustomerIdentity.model_validate(identity)
        limits = HistoryLimits.model_validate(limits)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN")
                row = connection.execute(
                    "SELECT 1 FROM sessions WHERE session_id = ? AND customer_id IS ?",
                    (str(session_id), identity.customer_id if identity else None),
                ).fetchone()
                if row is None:
                    raise SessionAccessError("Conversation session is inaccessible")
                rows = connection.execute(
                    "SELECT user_message, answer FROM turns WHERE session_id = ? "
                    "ORDER BY sequence DESC LIMIT ?",
                    (str(session_id), limits.max_turns),
                ).fetchall()
                # A contiguous suffix of complete turns; never skip a newer oversized turn.
                selected: list[tuple[str, str]] = []
                characters = 0
                for user_message, answer in rows:
                    size = len(user_message) + len(answer)
                    if characters + size > limits.max_characters:
                        break
                    selected.append((user_message, answer))
                    characters += size
                history = tuple(
                    message
                    for user_message, answer in reversed(selected)
                    for message in (
                        ConversationMessage(role="user", content=user_message),
                        ConversationMessage(role="assistant", content=answer),
                    )
                )
                return ConversationSnapshot(
                    session=ConversationSession(session_id=session_id, owner=identity),
                    history=history,
                )
        except (sqlite3.Error, ValidationError, ValueError) as exc:
            raise ConversationPersistenceError(
                "Conversation history could not be loaded"
            ) from exc

    def load_full(
        self, session_id: UUID, identity: CustomerIdentity | None
    ) -> ConversationTranscript:
        """Load every completed turn for an owned history view."""
        if identity is not None:
            identity = CustomerIdentity.model_validate(identity)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN")
                row = connection.execute(
                    "SELECT 1 FROM sessions WHERE session_id = ? AND customer_id IS ?",
                    (str(session_id), identity.customer_id if identity else None),
                ).fetchone()
                if row is None:
                    raise SessionAccessError("Conversation session is inaccessible")
                rows = connection.execute(
                    "SELECT user_message, answer FROM turns "
                    "WHERE session_id = ? ORDER BY sequence",
                    (str(session_id),),
                ).fetchall()
                if not rows:
                    raise SessionAccessError("Conversation session is inaccessible")
                messages = tuple(
                    message
                    for user_message, answer in rows
                    for message in (
                        ConversationMessage(role="user", content=user_message),
                        ConversationMessage(role="assistant", content=answer),
                    )
                )
                return ConversationTranscript(
                    session_id=session_id,
                    messages=messages,
                )
        except (sqlite3.Error, ValidationError, ValueError) as exc:
            raise ConversationPersistenceError(
                "Conversation history could not be loaded"
            ) from exc

    def delete(self, session_id: UUID, identity: CustomerIdentity | None) -> None:
        """Permanently remove an owned session and its completed turns."""
        if identity is not None:
            identity = CustomerIdentity.model_validate(identity)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT 1 FROM sessions WHERE session_id = ? AND customer_id IS ?",
                    (str(session_id), identity.customer_id if identity else None),
                ).fetchone()
                if row is None:
                    raise SessionAccessError("Conversation session is inaccessible")
                connection.execute(
                    "DELETE FROM turns WHERE session_id = ?", (str(session_id),)
                )
                connection.execute(
                    "DELETE FROM sessions WHERE session_id = ?", (str(session_id),)
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise ConversationPersistenceError(
                "Conversation could not be deleted"
            ) from exc

    def append(
        self,
        session: ConversationSession,
        *,
        user_message: str,
        answer: str,
    ) -> None:
        user_message = ChatRequest(message=user_message).message
        context = ExecutionContext(
            identity=session.owner,
            session=session,
            history=(
                ConversationMessage(role="user", content=user_message),
                ConversationMessage(role="assistant", content=answer),
            ),
        )
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                if (
                    connection.execute(
                        "SELECT 1 FROM sessions WHERE session_id = ? AND customer_id IS ?",
                        (
                            str(session.session_id),
                            session.owner.customer_id if session.owner else None,
                        ),
                    ).fetchone()
                    is None
                ):
                    raise SessionAccessError("Conversation session is inaccessible")
                sequence = connection.execute(
                    "SELECT coalesce(max(sequence), 0) + 1 FROM turns WHERE session_id = ?",
                    (str(session.session_id),),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO turns (session_id, sequence, user_message, answer) VALUES (?, ?, ?, ?)",
                    (
                        str(session.session_id),
                        sequence,
                        user_message,
                        context.history[1].content,
                    ),
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise ConversationPersistenceError(
                "Conversation turn could not be saved"
            ) from exc
