"""Owned operational schema; unrelated databases are never initialized or queried."""

import sqlite3

APPLICATION_ID = 0x454D4F52
SCHEMA_VERSION = 1
SCHEMA = {
    "customers": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY CHECK(customer_id > 0))",
    "products": "CREATE TABLE products (product_id INTEGER PRIMARY KEY CHECK(product_id > 0), name TEXT NOT NULL CHECK(length(trim(name)) > 0))",
    "orders": "CREATE TABLE orders (order_id INTEGER PRIMARY KEY CHECK(order_id > 0), customer_id INTEGER NOT NULL REFERENCES customers(customer_id), order_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('delivered', 'shipped', 'confirmed', 'pending', 'cancelled')), total_centavos INTEGER NOT NULL CHECK(typeof(total_centavos) = 'integer' AND total_centavos > 0), tracking_code TEXT, estimated_delivery TEXT)",
    "order_items": "CREATE TABLE order_items (order_id INTEGER NOT NULL REFERENCES orders(order_id), product_id INTEGER NOT NULL REFERENCES products(product_id), quantity INTEGER NOT NULL CHECK(typeof(quantity) = 'integer' AND quantity > 0), PRIMARY KEY(order_id, product_id))",
    "metadata": "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
}


def validate_schema(
    connection: sqlite3.Connection, *, allow_empty: bool = False
) -> bool:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    application_id = connection.execute("PRAGMA application_id").fetchone()[0]
    objects = dict(
        connection.execute(
            "SELECT name, sql FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT GLOB 'sqlite_*'"
        ).fetchall()
    )
    if allow_empty and version == 0 and application_id == 0 and not objects:
        return True
    if (
        version != SCHEMA_VERSION
        or application_id != APPLICATION_ID
        or objects != SCHEMA
    ):
        raise ValueError("Incompatible operational snapshot")
    return False
