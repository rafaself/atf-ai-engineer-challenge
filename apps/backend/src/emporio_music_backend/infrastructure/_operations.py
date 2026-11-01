"""Owned operational schema; unrelated databases are never initialized or queried."""

import sqlite3

APPLICATION_ID = 0x454D4F52
SCHEMA_VERSION = 1
SCHEMA = {
    "customers": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY CHECK(customer_id > 0))",
    "products": "CREATE TABLE products (product_id INTEGER PRIMARY KEY CHECK(product_id > 0), name TEXT NOT NULL CHECK(length(trim(name)) > 0))",
    "orders": "CREATE TABLE orders (order_id INTEGER PRIMARY KEY CHECK(order_id > 0), customer_id INTEGER NOT NULL REFERENCES customers(customer_id), order_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('delivered', 'shipped', 'confirmed', 'pending', 'cancelled')), total_centavos INTEGER NOT NULL CHECK(typeof(total_centavos) = 'integer' AND total_centavos > 0), tracking_code TEXT, estimated_delivery TEXT)",
    "order_items": "CREATE TABLE order_items (order_id INTEGER NOT NULL REFERENCES orders(order_id), product_id INTEGER NOT NULL REFERENCES products(product_id), quantity INTEGER NOT NULL CHECK(typeof(quantity) = 'integer' AND quantity > 0), PRIMARY KEY(order_id, product_id))",
}


def validate_schema(
    connection: sqlite3.Connection, *, allow_empty: bool = False
) -> bool:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    application_id = connection.execute("PRAGMA application_id").fetchone()[0]
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if allow_empty and version == 0 and application_id == 0 and not tables:
        return True
    if (
        version != SCHEMA_VERSION
        or application_id != APPLICATION_ID
        or not SCHEMA.keys() <= tables
    ):
        raise ValueError("Incompatible operational snapshot")
    for table, columns in {
        "customers": "customer_id",
        "products": "product_id, name",
        "orders": "order_id, customer_id, order_date, status, total_centavos, tracking_code, estimated_delivery",
        "order_items": "order_id, product_id, quantity",
    }.items():
        connection.execute(f"SELECT {columns} FROM {table} LIMIT 0")
    return False
