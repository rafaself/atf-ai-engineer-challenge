"""Validate and atomically import a complete catalog snapshot.

Run as a module with explicit --products, --categories, and --database paths.
"""

import argparse
import csv
import json
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Never

from emporio_music_backend.diagnostics import trace
from emporio_music_backend.infrastructure._catalog import (
    MAX_INTEGER,
    SCHEMA,
    SCHEMA_VERSION,
    normalize_lookup,
    validate_schema,
)

CATEGORY_COLUMNS = ("category_id", "name", "description")
PRODUCT_COLUMNS = (
    "product_id",
    "price_brl",
    "name",
    "category_id",
    "description",
    "stock_quantity",
    "status",
    "specs",
    "created_at",
)


class CatalogImportError(Exception):
    """A source validation or catalog persistence failure with safe diagnostics."""

    def __init__(self, path: Path, line: int | None, field: str, reason: str) -> None:
        location = f"{path}:{line}" if line is not None else str(path)
        super().__init__(f"{location}: {field}: {reason}")


@dataclass(frozen=True)
class ImportReport:
    categories: int
    products: int


def _read_rows(
    path: Path, columns: tuple[str, ...]
) -> list[tuple[int, dict[str, str]]]:
    line = 1
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            if len(header) != len(columns) or set(header) != set(columns):
                raise CatalogImportError(
                    path, 1, "header", "expected unique supplied columns"
                )
            rows = []
            for cells in reader:
                line = reader.line_num
                if len(cells) != len(header):
                    raise CatalogImportError(
                        path, line, "row", "incorrect number of fields"
                    )
                rows.append((line, dict(zip(header, cells, strict=True))))
            if not rows:
                raise CatalogImportError(
                    path, 2, "rows", "empty snapshots are not allowed"
                )
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        if isinstance(exc, csv.Error):
            line = reader.line_num
        raise CatalogImportError(
            path, line, "file", "cannot read valid UTF-8 CSV"
        ) from exc


def _integer(path: Path, line: int, field: str, value: str, *, minimum: int = 1) -> int:
    stripped = value.strip()
    if not re.fullmatch(r"[0-9]+", stripped) or len(stripped.lstrip("0")) > 19:
        raise CatalogImportError(
            path, line, field, "expected a bounded unsigned integer"
        )
    number = int(stripped.lstrip("0") or "0")
    if not minimum <= number <= MAX_INTEGER:
        raise CatalogImportError(path, line, field, "integer outside supported range")
    return number


def _text(path: Path, line: int, field: str, value: str) -> str:
    if not value.strip():
        raise CatalogImportError(path, line, field, "required text is blank")
    return value


def _lookup(path: Path, line: int, value: str) -> str:
    normalized = normalize_lookup(value)
    if not normalized:
        raise CatalogImportError(path, line, "name", "normalized name is empty")
    return normalized


def _price(path: Path, line: int, value: str) -> int:
    try:
        amount = Decimal(value.strip())
        if (
            not amount.is_finite()
            or amount <= 0
            or amount > Decimal("92233720368547758.07")
        ):
            raise ValueError
        parts = amount.as_tuple()
        assert isinstance(parts.exponent, int)
        digits = "".join(str(digit) for digit in parts.digits)
        shift = parts.exponent + 2
        if shift < 0:
            if -shift >= len(digits) or any(digit != "0" for digit in digits[shift:]):
                raise ValueError
            digits = digits[:shift]
        else:
            if len(digits) + shift > 19:
                raise ValueError
            digits += "0" * shift
        return int(digits)
    except (InvalidOperation, ValueError) as exc:
        raise CatalogImportError(
            path,
            line,
            "price_brl",
            "expected positive finite BRL with exact supported centavos",
        ) from exc


def _reject_constant(value: str) -> Never:
    raise ValueError("non-finite JSON constant")


def _validate_categories(path: Path) -> list[tuple[int, str, str, str]]:
    records = []
    ids: set[int] = set()
    names: set[str] = set()
    for line, row in _read_rows(path, CATEGORY_COLUMNS):
        identifier = _integer(path, line, "category_id", row["category_id"])
        if identifier in ids:
            raise CatalogImportError(path, line, "category_id", "duplicate identifier")
        ids.add(identifier)
        name = _text(path, line, "name", row["name"])
        normalized = _lookup(path, line, name)
        if normalized in names:
            raise CatalogImportError(
                path, line, "name", "duplicate normalized category"
            )
        names.add(normalized)
        records.append(
            (
                identifier,
                name,
                _text(path, line, "description", row["description"]),
                normalized,
            )
        )
    return records


def _validate_products(path: Path, categories: set[int]) -> list[tuple[int | str, ...]]:
    records: list[tuple[int | str, ...]] = []
    ids: set[int] = set()
    for line, row in _read_rows(path, PRODUCT_COLUMNS):
        identifier = _integer(path, line, "product_id", row["product_id"])
        if identifier in ids:
            raise CatalogImportError(path, line, "product_id", "duplicate identifier")
        ids.add(identifier)
        category = _integer(path, line, "category_id", row["category_id"])
        if category not in categories:
            raise CatalogImportError(
                path, line, "category_id", "unknown category reference"
            )
        name = _text(path, line, "name", row["name"])
        description = _text(path, line, "description", row["description"])
        price = _price(path, line, row["price_brl"])
        stock = _integer(path, line, "stock_quantity", row["stock_quantity"], minimum=0)
        if row["status"] not in {"active", "discontinued", "coming_soon"}:
            raise CatalogImportError(path, line, "status", "unsupported product status")
        try:
            specs = json.loads(
                row["specs"], parse_constant=_reject_constant, parse_float=Decimal
            )
            if not isinstance(specs, dict):
                raise ValueError
        except (ValueError, RecursionError, InvalidOperation) as exc:
            raise CatalogImportError(
                path, line, "specs", "expected a finite JSON object"
            ) from exc
        try:
            created = date.fromisoformat(row["created_at"])
            if created.isoformat() != row["created_at"]:
                raise ValueError
        except ValueError as exc:
            raise CatalogImportError(
                path, line, "created_at", "expected a valid YYYY-MM-DD date"
            ) from exc
        records.append(
            (
                identifier,
                category,
                name,
                description,
                price,
                stock,
                row["status"],
                row["specs"],
                row["created_at"],
                _lookup(path, line, name),
            )
        )
    return records


def import_catalog(
    products_path: Path, categories_path: Path, database_path: Path
) -> ImportReport:
    """Validate both sources first, then replace the owned catalog atomically."""
    trace(
        "catalog.import.started",
        products_file=products_path.name,
        categories_file=categories_path.name,
    )
    categories = _validate_categories(categories_path)
    products = _validate_products(products_path, {row[0] for row in categories})
    if database_path.resolve() in {products_path.resolve(), categories_path.resolve()}:
        raise CatalogImportError(
            database_path, None, "database", "must not overwrite a source"
        )
    try:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database_path, autocommit=True)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            try:
                if validate_schema(connection, allow_empty=True):
                    for statement in SCHEMA.values():
                        connection.execute(statement)
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                connection.execute("DELETE FROM products")
                connection.execute("DELETE FROM categories")
                connection.executemany(
                    "INSERT INTO categories VALUES (?, ?, ?, ?)", categories
                )
                connection.executemany(
                    "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    products,
                )
                connection.execute("COMMIT")
            except BaseException:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise CatalogImportError(database_path, None, "database", str(exc)) from exc
    trace(
        "catalog.import.completed", categories=len(categories), products=len(products)
    )
    return ImportReport(categories=len(categories), products=len(products))


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a complete catalog snapshot")
    parser.add_argument("--products", required=True, type=Path)
    parser.add_argument("--categories", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        report = import_catalog(
            arguments.products, arguments.categories, arguments.database
        )
    except CatalogImportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Imported {report.categories} categories and {report.products} products")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
