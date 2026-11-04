"""Real SQLite ownership, restart, bounded-history, and atomic-write contracts."""

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from emporio_music.domain.conversations import (
    ConversationSession,
    HistoryLimits,
)
from emporio_music.domain.errors import (
    ConversationPersistenceError,
    SessionAccessError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)


def test_repository_creates_grouped_storage_parent(tmp_path: Path) -> None:
    path = tmp_path / "conversations" / "conversations.sqlite3"

    repository = SQLiteConversationRepository(path)

    assert repository.database_path == path
    assert path.is_file()


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


def test_history_lists_completed_sessions_by_recent_activity_and_loads_full_transcript(
    conversations: SQLiteConversationRepository,
) -> None:
    owner = CustomerIdentity(customer_id=1)
    stranger = CustomerIdentity(customer_id=2)
    older = conversations.create(owner)
    conversations.append(
        older, user_message="Primeira pergunta", answer="Primeira resposta"
    )
    conversations.append(older, user_message="Acompanhamento", answer="Resposta final")
    newer = conversations.create(owner)
    conversations.append(newer, user_message="Outra conversa", answer="Outra resposta")
    empty = conversations.create(owner)
    foreign = conversations.create(stranger)
    conversations.append(foreign, user_message="Privada", answer="Não mostrar")

    items = conversations.list_for(owner)
    assert [(item.session_id, item.title) for item in items] == [
        (newer.session_id, "Outra conversa"),
        (older.session_id, "Primeira pergunta"),
    ]
    transcript = conversations.load_full(older.session_id, owner)
    assert transcript.session_id == older.session_id
    assert [(message.role, message.content) for message in transcript.messages] == [
        ("user", "Primeira pergunta"),
        ("assistant", "Primeira resposta"),
        ("user", "Acompanhamento"),
        ("assistant", "Resposta final"),
    ]
    assert empty.session_id not in {item.session_id for item in items}

    conversations.append(older, user_message="Retomada", answer="Última resposta")
    assert [item.session_id for item in conversations.list_for(owner)] == [
        older.session_id,
        newer.session_id,
    ]


def test_delete_history_removes_only_the_owned_conversation(
    conversations: SQLiteConversationRepository,
) -> None:
    owner = CustomerIdentity(customer_id=1)
    other_owner = CustomerIdentity(customer_id=2)
    first = conversations.create(owner)
    second = conversations.create(owner)
    foreign = conversations.create(other_owner)
    for session, prompt in (
        (first, "Excluir"),
        (second, "Preservar"),
        (foreign, "Outro cliente"),
    ):
        conversations.append(session, user_message=prompt, answer="Resposta")

    conversations.delete(first.session_id, owner)

    assert [item.session_id for item in conversations.list_for(owner)] == [
        second.session_id
    ]
    assert [item.session_id for item in conversations.list_for(other_owner)] == [
        foreign.session_id
    ]
    with pytest.raises(SessionAccessError):
        conversations.load_full(first.session_id, owner)


@pytest.mark.parametrize("owner_id,stranger_id", [(1, 2), (1, None), (None, 1)])
def test_foreign_and_unknown_sessions_never_expose_or_append_history(
    tmp_path: Path,
    owner_id: int | None,
    stranger_id: int | None,
) -> None:
    repository = SQLiteConversationRepository(tmp_path / "conversations.sqlite3")
    owner = CustomerIdentity(customer_id=owner_id) if owner_id else None
    stranger = CustomerIdentity(customer_id=stranger_id) if stranger_id else None
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
