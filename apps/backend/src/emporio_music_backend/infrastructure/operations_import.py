"""Validate minimal customer/order facts and atomically replace their owned snapshot."""

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from emporio_music_backend.contracts.orders import OrderSummary
from emporio_music_backend.diagnostics import trace
from emporio_music_backend.infrastructure._catalog import (
    validate_schema as validate_catalog,
)
from emporio_music_backend.infrastructure._operations import (
    APPLICATION_ID,
    SCHEMA,
    SCHEMA_VERSION,
    validate_schema,
)
from emporio_music_backend.infrastructure.money import parse_centavos

CUSTOMER_COLUMNS = ("customer_id", "name", "phone", "email", "city")
ORDER_COLUMNS = (
    "order_id",
    "customer_id",
    "order_date",
    "status",
    "total_brl",
    "payment_method",
    "tracking_code",
    "estimated_delivery",
    "notes",
)
ITEM_COLUMNS = ("order_id", "quantity", "product_id")


class OperationsImportError(Exception):
    def __init__(self, source: str, line: int | None, field: str, reason: str) -> None:
        location = f"{source} row {line}" if line is not None else source
        super().__init__(f"{location}: {field}: {reason}")


@dataclass(frozen=True)
class OperationsImportReport:
    customers: int
    orders: int
    items: int


def _read_rows(
    path: Path, source: str, columns: tuple[str, ...]
) -> tuple[list[tuple[int, dict[str, str]]], str]:
    try:
        raw = path.read_bytes()
        reader = csv.reader(
            io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True
        )
        header = next(reader, [])
        if len(header) != len(columns) or set(header) != set(columns):
            raise OperationsImportError(
                source, 1, "header", "expected unique supplied columns"
            )
        rows = []
        for cells in reader:
            if len(cells) != len(header):
                raise OperationsImportError(
                    source, reader.line_num, "row", "incorrect number of fields"
                )
            rows.append((reader.line_num, dict(zip(header, cells, strict=True))))
        return rows, hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, csv.Error) as exc:
        raise OperationsImportError(
            source, None, "file", "cannot read valid UTF-8 CSV"
        ) from exc


def _integer(value: str, source: str, line: int, field: str) -> int:
    value = value.strip()
    if not re.fullmatch(r"[0-9]+", value) or len(value.lstrip("0")) > 19:
        raise OperationsImportError(
            source, line, field, "expected a bounded positive integer"
        )
    result = int(value.lstrip("0") or "0")
    if not 0 < result <= 2**63 - 1:
        raise OperationsImportError(
            source, line, field, "integer outside supported range"
        )
    return result


def _date(value: str, source: str, line: int, field: str) -> date:
    try:
        parsed = date.fromisoformat(value.strip())
        if parsed.isoformat() != value.strip():
            raise ValueError
        return parsed
    except ValueError as exc:
        raise OperationsImportError(
            source, line, field, "expected a valid YYYY-MM-DD date"
        ) from exc


def import_operations(
    customers_path: Path,
    orders_path: Path,
    items_path: Path,
    catalog_path: Path,
    database_path: Path,
) -> OperationsImportReport:
    destination = database_path.resolve()
    for source in (customers_path, orders_path, items_path, catalog_path):
        if destination == source.resolve() or (
            destination.exists() and source.exists() and destination.samefile(source)
        ):
            raise OperationsImportError(
                "database", None, "path", "must not overwrite an input"
            )
    customers, customers_hash = _read_rows(
        customers_path, "customers", CUSTOMER_COLUMNS
    )
    orders, orders_hash = _read_rows(orders_path, "orders", ORDER_COLUMNS)
    items, items_hash = _read_rows(items_path, "order_items", ITEM_COLUMNS)
    customer_ids: set[int] = set()
    for line, row in customers:
        identifier = _integer(row["customer_id"], "customers", line, "customer_id")
        if identifier in customer_ids:
            raise OperationsImportError(
                "customers", line, "customer_id", "duplicate identifier"
            )
        customer_ids.add(identifier)
    if not customer_ids:
        raise OperationsImportError(
            "customers", None, "rows", "at least one customer is required"
        )
    order_ids: set[int] = set()
    order_records: list[tuple[int | str | None, ...]] = []
    for line, row in orders:
        order_id = _integer(row["order_id"], "orders", line, "order_id")
        customer_id = _integer(row["customer_id"], "orders", line, "customer_id")
        if order_id in order_ids or customer_id not in customer_ids:
            raise OperationsImportError(
                "orders",
                line,
                "identifier",
                "duplicate order or unknown customer reference",
            )
        order_ids.add(order_id)
        ordered = _date(row["order_date"], "orders", line, "order_date")
        estimated = (
            _date(row["estimated_delivery"], "orders", line, "estimated_delivery")
            if row["estimated_delivery"].strip()
            else None
        )
        try:
            total = parse_centavos(row["total_brl"])
            summary = OrderSummary.model_validate(
                {
                    "order_id": order_id,
                    "order_date": ordered,
                    "status": row["status"],
                    "total_centavos": total,
                }
            )
        except (ValueError, ValidationError) as exc:
            raise OperationsImportError(
                "orders",
                line,
                "status/total_brl",
                "expected a supported status and exact positive total",
            ) from exc
        order_records.append(
            (
                order_id,
                customer_id,
                summary.order_date.isoformat(),
                summary.status,
                summary.total_centavos,
                row["tracking_code"].strip() or None,
                estimated.isoformat() if estimated else None,
            )
        )
    try:
        with closing(
            sqlite3.connect(catalog_path.resolve().as_uri() + "?mode=ro", uri=True)
        ) as connection:
            connection.execute("BEGIN")
            validate_catalog(connection)
            product_names = dict(
                connection.execute("SELECT product_id, name FROM products").fetchall()
            )
    except (sqlite3.Error, ValueError) as exc:
        raise OperationsImportError(
            "catalog", None, "snapshot", "cannot read a compatible catalog"
        ) from exc
    item_records: list[tuple[int, int, int]] = []
    pairs: set[tuple[int, int]] = set()
    references: set[int] = set()
    for line, row in items:
        order_id = _integer(row["order_id"], "order_items", line, "order_id")
        product_id = _integer(row["product_id"], "order_items", line, "product_id")
        quantity = _integer(row["quantity"], "order_items", line, "quantity")
        pair = order_id, product_id
        if (
            pair in pairs
            or order_id not in order_ids
            or product_id not in product_names
        ):
            raise OperationsImportError(
                "order_items",
                line,
                "reference",
                "duplicate pair or unknown order/product reference",
            )
        pairs.add(pair)
        references.add(product_id)
        item_records.append((order_id, product_id, quantity))
    products = [
        (identifier, product_names[identifier]) for identifier in sorted(references)
    ]
    reference_hash = hashlib.sha256(
        json.dumps(products, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    metadata = {
        "customers_sha256": customers_hash,
        "orders_sha256": orders_hash,
        "order_items_sha256": items_hash,
        "catalog_references_sha256": reference_hash,
    }
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(descriptor)
        with closing(sqlite3.connect(destination, autocommit=True)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            try:
                if validate_schema(connection, allow_empty=True):
                    for statement in SCHEMA.values():
                        connection.execute(statement)
                    connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                destination.chmod(0o600)
                for table in (
                    "order_items",
                    "orders",
                    "products",
                    "customers",
                    "metadata",
                ):
                    connection.execute(f"DELETE FROM {table}")
                connection.executemany(
                    "INSERT INTO customers VALUES (?)",
                    [(key,) for key in sorted(customer_ids)],
                )
                connection.executemany("INSERT INTO products VALUES (?, ?)", products)
                connection.executemany(
                    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", order_records
                )
                connection.executemany(
                    "INSERT INTO order_items VALUES (?, ?, ?)", item_records
                )
                connection.executemany(
                    "INSERT INTO metadata VALUES (?, ?)", metadata.items()
                )
                connection.execute("COMMIT")
            except BaseException:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise OperationsImportError(
            "database",
            None,
            "snapshot",
            "cannot replace a compatible operational snapshot",
        ) from exc
    trace(
        "operations.import.completed",
        customers=len(customer_ids),
        orders=len(order_records),
        items=len(item_records),
    )
    return OperationsImportReport(
        len(customer_ids), len(order_records), len(item_records)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import the fictional customer/order snapshot"
    )
    for flag in ("customers", "orders", "order-items", "catalog", "database"):
        parser.add_argument("--" + flag, required=True, type=Path)
    args = parser.parse_args()
    try:
        report = import_operations(
            args.customers, args.orders, args.order_items, args.catalog, args.database
        )
    except OperationsImportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Imported {report.customers} customers, {report.orders} orders and {report.items} items"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
