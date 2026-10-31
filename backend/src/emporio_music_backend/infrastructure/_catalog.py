"""Shared catalog schema and lookup normalization."""

import sqlite3
import unicodedata

SCHEMA_VERSION = 1
MAX_INTEGER = 2**63 - 1
SCHEMA = {
    "categories": """CREATE TABLE categories (
        category_id INTEGER PRIMARY KEY CHECK(category_id > 0),
        name TEXT NOT NULL CHECK(length(trim(name)) > 0),
        description TEXT NOT NULL CHECK(length(trim(description)) > 0),
        normalized_name TEXT NOT NULL UNIQUE CHECK(length(normalized_name) > 0)
    )""",
    "products": """CREATE TABLE products (
        product_id INTEGER PRIMARY KEY CHECK(product_id > 0),
        category_id INTEGER NOT NULL REFERENCES categories(category_id),
        name TEXT NOT NULL CHECK(length(trim(name)) > 0),
        description TEXT NOT NULL CHECK(length(trim(description)) > 0),
        price_centavos INTEGER NOT NULL CHECK(typeof(price_centavos) = 'integer' AND price_centavos > 0),
        stock_quantity INTEGER NOT NULL CHECK(typeof(stock_quantity) = 'integer' AND stock_quantity >= 0),
        status TEXT NOT NULL CHECK(status IN ('active', 'discontinued', 'coming_soon')),
        specs TEXT NOT NULL,
        created_at TEXT NOT NULL,
        normalized_name TEXT NOT NULL CHECK(length(normalized_name) > 0)
    )""",
}


def normalize_lookup(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value.strip().casefold())
        if not unicodedata.combining(char)
    )


def validate_schema(
    connection: sqlite3.Connection, *, allow_empty: bool = False
) -> bool:
    """Return whether a new schema is needed; never modify existing structures."""
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    objects = dict(
        connection.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type IN ('table', 'view') AND name NOT GLOB 'sqlite_*'"
        ).fetchall()
    )
    if allow_empty and version == 0 and not objects:
        return True
    if version != SCHEMA_VERSION or objects != SCHEMA:
        raise ValueError("database is not a compatible schema-version-1 catalog")
    return False
