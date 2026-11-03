"""Explicit local source-data and persistent runtime storage locations."""

import os
from pathlib import Path

_configured_data_directory = Path(
    os.environ.get("EMPORIO_MUSIC_DATA_DIR", "data")
).expanduser()
DATA_DIRECTORY = _configured_data_directory.resolve()
CATALOG_DATABASE_PATH = DATA_DIRECTORY / "catalog.sqlite3"
OPERATIONS_DATABASE_PATH = DATA_DIRECTORY / "operations.sqlite3"
CONVERSATION_DATABASE_PATH = DATA_DIRECTORY / "conversations.sqlite3"
