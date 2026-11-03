"""Default tests never contact a real model, even if credentials are present."""

import shutil
from pathlib import Path

import pytest
from emporio_music import paths
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.catalog_import import import_catalog
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music.infrastructure.operations_import import import_operations
from pydantic_ai import models

REPOSITORY_ROOT = Path(__file__).resolve().parent


@pytest.fixture(autouse=True)
def forbid_live_model_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


@pytest.fixture(autouse=True)
def isolate_agent_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep local model selections and budgets from affecting controlled tests."""
    for name in (
        "BEDROCK_MODEL_ID",
        "AWS_PROFILE",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AGENT_MAX_REQUESTS",
        "AGENT_MAX_TOOL_CALLS",
        "AGENT_MAX_OUTPUT_TOKENS",
        "AGENT_REQUEST_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def conversations(tmp_path: "Path") -> "SQLiteConversationRepository":
    return SQLiteConversationRepository(tmp_path / "conversations.sqlite3")


@pytest.fixture
def trusted_context() -> "ExecutionContext":
    return ExecutionContext(identity=CustomerIdentity(customer_id=1))


@pytest.fixture
def operational_database(tmp_path: Path) -> Path:
    data = REPOSITORY_ROOT / "data"
    catalog = tmp_path / "operational-catalog.sqlite3"
    database = tmp_path / "operations.sqlite3"
    import_catalog(
        data / "catalog" / "products.csv",
        data / "catalog" / "categories.csv",
        data / "catalog" / "promotions.csv",
        catalog,
    )
    import_operations(
        data / "operations" / "customers.csv",
        data / "operations" / "orders.csv",
        data / "operations" / "order_items.csv",
        catalog,
        database,
    )
    return database


@pytest.fixture
def fixed_demo_identity(
    monkeypatch: pytest.MonkeyPatch, operational_database: Path
) -> CustomerIdentity:
    monkeypatch.setattr(paths, "OPERATIONS_DATABASE_PATH", operational_database)
    return CustomerIdentity(customer_id=1)


@pytest.fixture
def project_copy(tmp_path: Path) -> Path:
    """Run package commands against isolated source and runtime data."""
    project = tmp_path / "project"
    source = project / "packages/emporio_music/src"
    shutil.copytree(
        REPOSITORY_ROOT / "packages/emporio_music/src",
        source,
        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
    )
    data = project / "data"
    data.mkdir()
    for path in (REPOSITORY_ROOT / "data").rglob("*.csv"):
        destination = data / path.relative_to(REPOSITORY_ROOT / "data")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    return project
