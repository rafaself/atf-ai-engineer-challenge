"""Fixed local-demo storage, independent of the launch directory."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIRECTORY = PROJECT_ROOT / "data"
CATALOG_DATABASE_PATH = DATA_DIRECTORY / "catalog.sqlite3"
OPERATIONS_DATABASE_PATH = DATA_DIRECTORY / "operations.sqlite3"
CONVERSATION_DATABASE_PATH = DATA_DIRECTORY / "conversations.sqlite3"
CHROMA_STORAGE_PATH = DATA_DIRECTORY / "chroma"
