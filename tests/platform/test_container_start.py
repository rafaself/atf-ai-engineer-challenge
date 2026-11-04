"""Container startup installs ready snapshots without replacing conversations."""

import shutil
from pathlib import Path

from emporio_music.container_start import initialize_data
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.conversations import SQLiteConversationRepository
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository

from tests._support import REPOSITORY_ROOT


def test_fresh_volume_and_restart_have_data_and_preserve_history(
    tmp_path: Path, operational_database: Path
) -> None:
    seed = tmp_path / "seed"
    runtime = tmp_path / "runtime"
    for name in ("catalog", "operations", "policies"):
        shutil.copytree(
            REPOSITORY_ROOT / "data" / name,
            seed / name,
            ignore=shutil.ignore_patterns(
                "*.sqlite3*", "policy-indexes", "policy-benchmark-indexes"
            ),
        )
    shutil.copy2(operational_database, seed / "operations" / "operations.sqlite3")
    shutil.copy2(
        operational_database.parent / "operational-catalog.sqlite3",
        seed / "catalog" / "catalog.sqlite3",
    )
    seed_index = seed / "policies" / "policy-indexes"
    seed_index.mkdir(exist_ok=True)
    (seed_index / "snapshot").write_text("current index")

    initialize_data(seed, runtime)

    owner = CustomerIdentity(customer_id=1)
    assert SQLiteOrderRepository(runtime / "operations" / "operations.sqlite3").exists(
        owner
    )
    assert (runtime / "catalog" / "catalog.sqlite3").is_file()
    assert (runtime / "policies" / "policy-indexes" / "snapshot").read_text() == (
        "current index"
    )
    for source in seed.rglob("*"):
        if source.is_file():
            assert (
                runtime / source.relative_to(seed)
            ).read_bytes() == source.read_bytes()

    history = SQLiteConversationRepository(
        runtime / "conversations" / "conversations.sqlite3"
    )
    session = history.create(owner)
    history.append(session, user_message="Meu pedido", answer="Como posso ajudar?")
    (runtime / "policies" / "policy-indexes" / "old-index-file").touch()
    (runtime / "catalog" / "products.csv").write_text("stale source")

    initialize_data(seed, runtime)

    assert not (runtime / "policies" / "policy-indexes" / "old-index-file").exists()
    assert (runtime / "catalog" / "products.csv").read_bytes() == (
        seed / "catalog" / "products.csv"
    ).read_bytes()
    restored = SQLiteConversationRepository(history.database_path)
    assert [
        m.content for m in restored.load_full(session.session_id, owner).messages
    ] == [
        "Meu pedido",
        "Como posso ajudar?",
    ]
