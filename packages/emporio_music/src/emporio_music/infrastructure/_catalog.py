"""Shared catalog schema and lookup normalization."""

import sqlite3
import unicodedata

SCHEMA_VERSION = 2
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
    "promotions": """CREATE TABLE promotions (
        promotion_id INTEGER PRIMARY KEY CHECK(promotion_id > 0),
        product_id INTEGER NOT NULL REFERENCES products(product_id),
        discount_percent INTEGER NOT NULL CHECK(typeof(discount_percent) = 'integer' AND discount_percent BETWEEN 1 AND 100),
        description TEXT NOT NULL CHECK(length(trim(description)) > 0),
        is_active INTEGER NOT NULL CHECK(typeof(is_active) = 'integer' AND is_active IN (0, 1))
    )""",
}


def normalize_lookup(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip().casefold())
    normalized = "".join(
        "-" if unicodedata.category(char) == "Pd" else char for char in normalized
    )
    return "".join(char for char in normalized if not unicodedata.combining(char))


def validate_schema(
    connection: sqlite3.Connection, *, allow_empty: bool = False
) -> bool:
    """Return whether a new schema is needed; never modify existing structures."""
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if allow_empty and version == 0 and not tables:
        return True
    if version != SCHEMA_VERSION or not SCHEMA.keys() <= tables:
        raise ValueError("database is not a compatible catalog")
    for table, columns in {
        "categories": "category_id, name, description, normalized_name",
        "products": "product_id, category_id, name, description, price_centavos, stock_quantity, status, specs, created_at, normalized_name",
        "promotions": "promotion_id, product_id, discount_percent, description, is_active",
    }.items():
        connection.execute(f"SELECT {columns} FROM {table} LIMIT 0")
    return False
