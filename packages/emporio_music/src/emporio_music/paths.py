"""Explicit local source-data and persistent runtime storage locations."""

import os
from pathlib import Path

_configured_data_directory = Path(
    os.environ.get("EMPORIO_MUSIC_DATA_DIR", "data")
).expanduser()
DATA_DIRECTORY = _configured_data_directory.resolve()
CATALOG_DIRECTORY = DATA_DIRECTORY / "catalog"
OPERATIONS_DIRECTORY = DATA_DIRECTORY / "operations"
POLICIES_DIRECTORY = DATA_DIRECTORY / "policies"
CONVERSATIONS_DIRECTORY = DATA_DIRECTORY / "conversations"

CATALOG_DATABASE_PATH = CATALOG_DIRECTORY / "catalog.sqlite3"
OPERATIONS_DATABASE_PATH = OPERATIONS_DIRECTORY / "operations.sqlite3"
CONVERSATION_DATABASE_PATH = CONVERSATIONS_DIRECTORY / "conversations.sqlite3"
POLICY_INDEX_DIRECTORY = POLICIES_DIRECTORY / "policy-indexes"
