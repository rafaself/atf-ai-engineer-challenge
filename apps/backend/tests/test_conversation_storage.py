"""Real SQLite ownership, restart, bounded-history, and atomic-write contracts."""

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from emporio_music_backend.contracts import (
    ConversationSession,
    CustomerIdentity,
    HistoryLimits,
)
from emporio_music_backend.contracts.errors import (
    ConversationPersistenceError,
    SessionAccessError,
)
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)


def test_restart_history_limits_and_private_database(tmp_path: Path) -> None:
    path = tmp_path / "conversations.sqlite3"
    repository = SQLiteConversationRepository(path)
    owner = CustomerIdentity(customer_id=1)
    session = repository.create(owner)
    for user, answer in (("A", "one"), ("B", "two"), ("C", "three")):
        repository.append(session, user_message=user, answer=answer)
    path.chmod(0o644)  # An existing/externally copied database must also be private.
    restarted = SQLiteConversationRepository(path)
    state = restarted.load(
        session.session_id, owner, limits=HistoryLimits(max_turns=2, max_characters=10)
    )
    assert [m.content for m in state.history] == ["B", "two", "C", "three"]
    assert [m.role for m in state.history] == ["user", "assistant", "user", "assistant"]
    assert [
        m.content
        for m in restarted.load(
            session.session_id, owner, limits=HistoryLimits(max_characters=9)
        ).history
    ] == ["C", "three"]
    assert (
        restarted.load(
            session.session_id, owner, limits=HistoryLimits(max_characters=5)
        ).history
        == ()
    )
    assert (
        len(
            restarted.load(
                session.session_id, owner, limits=HistoryLimits(max_turns=1)
            ).history
        )
        == 2
    )
    assert path.stat().st_mode & 0o077 == 0


def test_foreign_and_unknown_sessions_never_expose_or_append_history(
    tmp_path: Path,
) -> None:
    repository = SQLiteConversationRepository(tmp_path / "conversations.sqlite3")
    owner = CustomerIdentity(customer_id=1)
    stranger = CustomerIdentity(customer_id=2)
    session = repository.create(owner)
    repository.append(session, user_message="Private", answer="Private answer")
    errors = []
    for session_id in (session.session_id, uuid4()):
        with pytest.raises(SessionAccessError) as error:
            repository.load(session_id, stranger, limits=HistoryLimits())
        errors.append(str(error.value))
    assert errors == ["Conversation session is inaccessible"] * 2
    with pytest.raises(SessionAccessError):
        repository.append(
            ConversationSession(session_id=session.session_id, owner=stranger),
            user_message="Forged",
            answer="No",
        )
    assert (
        len(repository.load(session.session_id, owner, limits=HistoryLimits()).history)
        == 2
    )


def test_failed_insert_preserves_the_previously_saved_turn(
    tmp_path: Path,
) -> None:
    path = tmp_path / "conversations.sqlite3"
    first = SQLiteConversationRepository(path)
    second = SQLiteConversationRepository(path)
    owner = CustomerIdentity(customer_id=1)
    session = first.create(owner)
    first.append(session, user_message="Accepted", answer="Saved")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TRIGGER fail_turn BEFORE INSERT ON turns BEGIN SELECT RAISE(ABORT, 'test storage fault'); END"
        )
    with pytest.raises(ConversationPersistenceError):
        first.append(session, user_message="Failed", answer="Not completed")
    state = second.load(session.session_id, owner, limits=HistoryLimits())
    assert [m.content for m in state.history] == [
        "Accepted",
        "Saved",
    ]


def test_foreign_database_is_untouched_and_missing_database_is_not_recreated(
    tmp_path: Path,
) -> None:
    path = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES ('preserved')")
    before = path.read_bytes()
    with pytest.raises(ConversationPersistenceError):
        SQLiteConversationRepository(path)
    assert path.read_bytes() == before
    owned = tmp_path / "owned.sqlite3"
    repository = SQLiteConversationRepository(owned)
    owner = CustomerIdentity(customer_id=1)
    session = repository.create(owner)
    owned.unlink()
    with pytest.raises(ConversationPersistenceError):
        repository.load(session.session_id, owner, limits=HistoryLimits())
    assert not owned.exists()
