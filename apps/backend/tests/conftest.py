"""Default tests never contact a real model, even if credentials are present."""

import json
from pathlib import Path

import pytest
from pydantic_ai import models

from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.infrastructure.catalog_import import import_catalog
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.infrastructure.operations_import import import_operations


@pytest.fixture(autouse=True)
def forbid_live_model_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


@pytest.fixture
def conversations(tmp_path: "Path") -> "SQLiteConversationRepository":
    return SQLiteConversationRepository(tmp_path / "conversations.sqlite3")


@pytest.fixture
def trusted_context() -> "ExecutionContext":
    return ExecutionContext(identity=CustomerIdentity(customer_id=1))


@pytest.fixture
def operational_database(tmp_path: Path) -> Path:
    data = Path(__file__).parents[3] / "data"
    catalog = tmp_path / "operational-catalog.sqlite3"
    database = tmp_path / "operations.sqlite3"
    import_catalog(
        data / "products.csv", data / "categories.csv", data / "promotions.csv", catalog
    )
    import_operations(
        data / "customers.csv",
        data / "orders.csv",
        data / "order_items.csv",
        catalog,
        database,
    )
    return database


@pytest.fixture
def api_headers(
    monkeypatch: pytest.MonkeyPatch, operational_database: Path
) -> dict[str, str]:
    monkeypatch.setenv("OPERATIONS_DATABASE_PATH", str(operational_database))
    # Synthetic test credentials only; the production adapter must still resolve them.
    token = "synthetic-api-customer-" + "a" * 32
    monkeypatch.setenv(
        "DEMO_CUSTOMER_TOKENS_JSON",
        json.dumps({token: 1, "synthetic-api-other-" + "b" * 32: 2}),
    )
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def other_headers(api_headers: dict[str, str]) -> dict[str, str]:
    return {"Authorization": "Bearer synthetic-api-other-" + "b" * 32}
