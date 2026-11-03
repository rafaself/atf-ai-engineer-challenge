"""Real SQLite snapshot replacement, exact facts and independent authorization."""

import csv
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from emporio_music.domain.errors import (
    AmbiguousTrackingCodeError,
    ConfigurationError,
    OperationalRetrievalError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.orders import (
    OrderListQuery,
    OrderLookupQuery,
    OrderTrackingCodeQuery,
)
from emporio_music.infrastructure.operations_import import (
    CUSTOMER_COLUMNS,
    ITEM_COLUMNS,
    ORDER_COLUMNS,
    OperationsImportError,
    import_operations,
)
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from pydantic import ValidationError

from tests._support import REPOSITORY_ROOT

DATA = REPOSITORY_ROOT / "data"


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> Path:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return path


def snapshot(tmp_path: Path, *, count: int = 23) -> tuple[Path, Path, Path]:
    customers = write_csv(
        tmp_path / "customers.csv",
        CUSTOMER_COLUMNS,
        [
            {
                "customer_id": 1,
                "name": "CONTACT-NAME",
                "phone": "private-phone",
                "email": "unrestricted-contact",
                "city": "private-city",
            },
            {"customer_id": 2},
            {"customer_id": 3},
        ],
    )
    orders = write_csv(
        tmp_path / "orders.csv",
        ORDER_COLUMNS,
        [
            {
                "order_id": n,
                "customer_id": 1 if n <= count else 2,
                "order_date": "2026-03-22" if n != 1 else "2025-12-31",
                "status": "shipped",
                "total_brl": "0.01",
                "tracking_code": "TRACKING-PRIVATE" if n == 1 else "",
                "estimated_delivery": "2026-04-01" if n == 1 else "",
                "notes": "PRIVATE-NOTES",
                "payment_method": "PRIVATE-PAYMENT",
            }
            for n in range(1, count + 2)
        ],
    )
    items = write_csv(
        tmp_path / "items.csv",
        ITEM_COLUMNS,
        [{"order_id": 1, "product_id": n + 80, "quantity": 2} for n in range(1, 23)],
    )
    return customers, orders, items


def test_original_import_is_repeatable_minimal_and_preserves_exact_totals(
    operational_database: Path,
) -> None:
    repository = SQLiteOrderRepository(operational_database)
    with sqlite3.connect(operational_database) as conn:
        assert conn.execute("SELECT count(*) FROM customers").fetchone()[0] == 50
        assert conn.execute("SELECT count(*) FROM orders").fetchone()[0] == 20
        assert conn.execute("SELECT count(*) FROM order_items").fetchone()[0] == 22
        assert [row[1] for row in conn.execute("PRAGMA table_info(customers)")] == [
            "customer_id"
        ]
        columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
        assert not columns & {
            "notes",
            "payment_method",
            "name",
            "email",
            "phone",
            "city",
        }
        rows_before = conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
    with (DATA / "operations" / "orders.csv").open(newline="") as stream:
        original = list(csv.DictReader(stream))
    row = original[0]
    detail = repository.get_order(
        CustomerIdentity(customer_id=int(row["customer_id"])),
        OrderLookupQuery(order_id=int(row["order_id"])),
    )
    assert detail is not None and Decimal(detail.total_brl) == Decimal(row["total_brl"])
    assert not hasattr(detail, "unit_price")
    assert operational_database.stat().st_mode & 0o777 == 0o600
    import_operations(
        DATA / "operations" / "customers.csv",
        DATA / "operations" / "orders.csv",
        DATA / "operations" / "order_items.csv",
        operational_database.parent / "operational-catalog.sqlite3",
        operational_database,
    )
    with sqlite3.connect(operational_database) as conn:
        assert (
            conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
            == rows_before
        )


def test_scoped_reads_limits_ordering_and_full_replacement(
    operational_database: Path, tmp_path: Path
) -> None:
    files = snapshot(tmp_path)
    catalog = operational_database.parent / "operational-catalog.sqlite3"
    import_operations(*files, catalog, operational_database)
    repository = SQLiteOrderRepository(operational_database)
    alice, bob, empty, unknown = (
        CustomerIdentity(customer_id=n) for n in (1, 2, 3, 999)
    )
    result = repository.list_orders(alice, OrderListQuery())
    assert [item.order_id for item in result.orders] == [23, 22, 21, 20, 19]
    assert result.total_matches == 23 and result.truncated
    assert len(repository.list_orders(alice, OrderListQuery(limit=20)).orders) == 20
    assert repository.list_orders(bob, OrderListQuery()).orders[0].order_id == 24
    assert repository.list_orders(empty, OrderListQuery()).total_matches == 0
    assert repository.get_order(alice, OrderLookupQuery(order_id=24)) is None
    assert repository.get_order(alice, OrderLookupQuery(order_id=999)) is None
    for query in (
        lambda: repository.list_orders(unknown, OrderListQuery()),
        lambda: repository.get_order(unknown, OrderLookupQuery(order_id=1)),
    ):
        with pytest.raises(ConfigurationError):
            query()
    detail = repository.get_order(alice, OrderLookupQuery(order_id=1))
    assert detail is not None
    assert [item.product_id for item in detail.items] == list(range(81, 101))
    assert all(item.quantity == 2 for item in detail.items)
    assert (
        detail.total_items == 22
        and detail.items_truncated
        and detail.total_centavos == 1
    )
    assert (
        detail.tracking_code == "TRACKING-PRIVATE"
        and str(detail.estimated_delivery) == "2026-04-01"
    )
    detail2 = repository.get_order(alice, OrderLookupQuery(order_id=2))
    assert (
        detail2 is not None
        and detail2.tracking_code is None
        and detail2.estimated_delivery is None
    )
    assert (
        not {"customer_id", "notes", "payment_method", "email", "phone", "city"}
        & detail.model_dump().keys()
    )
    # A valid empty snapshot removes all orders, products and items, retaining customers.
    write_csv(files[1], ORDER_COLUMNS, [])
    write_csv(files[2], ITEM_COLUMNS, [])
    import_operations(*files, catalog, operational_database)
    assert repository.list_orders(alice, OrderListQuery()).orders == ()
    with sqlite3.connect(operational_database) as conn:
        assert conn.execute("SELECT count(*) FROM products").fetchone()[0] == 0


def test_tracking_lookup_returns_only_an_owned_exact_match(
    operational_database: Path,
) -> None:
    repository = SQLiteOrderRepository(operational_database)
    owner = CustomerIdentity(customer_id=1)
    foreign_code = "BRJL5544332BR"
    owned_code = "BRQM7890123BR"

    owned = repository.get_order_by_tracking_code(
        owner, OrderTrackingCodeQuery(tracking_code=owned_code)
    )
    assert owned is not None
    assert owned == repository.get_order(owner, OrderLookupQuery(order_id=4))
    assert (
        repository.get_order_by_tracking_code(
            owner, OrderTrackingCodeQuery(tracking_code=foreign_code)
        )
        is None
    )
    assert (
        repository.get_order_by_tracking_code(
            owner, OrderTrackingCodeQuery(tracking_code="UNKNOWN-CODE")
        )
        is None
    )
    assert (
        repository.get_order_by_tracking_code(
            owner, OrderTrackingCodeQuery(tracking_code=f" {owned_code} ")
        )
        == owned
    )


def test_tracking_lookup_reports_duplicate_owned_codes(
    operational_database: Path,
) -> None:
    with sqlite3.connect(operational_database) as connection:
        connection.execute(
            "UPDATE orders SET customer_id = ?, tracking_code = ? WHERE order_id = ?",
            (1, "BRQM7890123BR", 8),
        )
    repository = SQLiteOrderRepository(operational_database)

    with pytest.raises(AmbiguousTrackingCodeError):
        repository.get_order_by_tracking_code(
            CustomerIdentity(customer_id=1),
            OrderTrackingCodeQuery(tracking_code="BRQM7890123BR"),
        )


@pytest.mark.parametrize("tracking_code", ["", "   ", "\n\t", None, 123])
def test_tracking_query_rejects_blank_or_non_text_codes(
    tracking_code: object,
) -> None:
    with pytest.raises(ValidationError):
        OrderTrackingCodeQuery.model_validate({"tracking_code": tracking_code})

    with pytest.raises(ValidationError):
        OrderTrackingCodeQuery.model_validate(
            {"tracking_code": "ABC", "customer_id": 2}
        )


@pytest.mark.parametrize(
    ("source", "field", "value"),
    [
        (0, "customer_id", "9223372036854775808"),
        (0, "customer_id", "0"),
        (0, "customer_id", "true"),
        (1, "order_date", "2026-02-30"),
        (1, "estimated_delivery", "not-a-date"),
        (1, "status", "invented"),
        (1, "total_brl", "0.001"),
        (1, "total_brl", "92233720368547758.08"),
        (1, "total_brl", "NaN"),
        (1, "customer_id", "999"),
        (2, "order_id", "999"),
        (2, "product_id", "999999"),
        (2, "quantity", "1.5"),
        (2, "quantity", "-1"),
        (2, "quantity", "9223372036854775808"),
    ],
)
def test_invalid_import_preserves_previous_snapshot(
    operational_database: Path, tmp_path: Path, source: int, field: str, value: str
) -> None:
    files = snapshot(tmp_path)
    path = files[source]
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())
    rows[0][field] = value
    write_csv(path, columns, rows)
    before = operational_database.read_bytes()
    with pytest.raises(OperationsImportError):
        import_operations(
            *files,
            operational_database.parent / "operational-catalog.sqlite3",
            operational_database,
        )
    assert operational_database.read_bytes() == before


@pytest.mark.parametrize("source", [0, 1, 2])
def test_duplicate_rows_and_malformed_headers_are_rejected(
    operational_database: Path, tmp_path: Path, source: int
) -> None:
    files = snapshot(tmp_path)
    with files[source].open(newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        columns = tuple(reader.fieldnames or ())
    before = operational_database.read_bytes()
    write_csv(files[source], columns, [*rows, rows[0]])
    with pytest.raises(OperationsImportError):
        import_operations(
            *files,
            operational_database.parent / "operational-catalog.sqlite3",
            operational_database,
        )
    write_csv(files[source], (*columns[:-1], columns[0]), [])
    with pytest.raises(OperationsImportError):
        import_operations(
            *files,
            operational_database.parent / "operational-catalog.sqlite3",
            operational_database,
        )
    assert operational_database.read_bytes() == before


def test_storage_faults_are_not_empty_and_foreign_databases_are_preserved(
    operational_database: Path, tmp_path: Path
) -> None:
    repository = SQLiteOrderRepository(operational_database)
    files = snapshot(tmp_path)
    catalog = operational_database.parent / "operational-catalog.sqlite3"
    foreign = tmp_path / "foreign.sqlite3"
    with sqlite3.connect(foreign) as conn:
        conn.execute("CREATE TABLE private (value TEXT)")
    before = foreign.read_bytes()
    with pytest.raises(OperationsImportError):
        import_operations(*files, catalog, foreign)
    assert before == foreign.read_bytes()
    with pytest.raises(ConfigurationError):
        SQLiteOrderRepository(foreign)
    with pytest.raises(OperationsImportError):
        import_operations(*files, catalog, files[0])
    with pytest.raises(OperationsImportError):
        import_operations(*files, catalog, catalog)
    operational_database.unlink()
    with pytest.raises(OperationalRetrievalError):
        repository.list_orders(CustomerIdentity(customer_id=1), OrderListQuery())
    with pytest.raises(OperationalRetrievalError):
        repository.get_order_by_tracking_code(
            CustomerIdentity(customer_id=1),
            OrderTrackingCodeQuery(tracking_code="BRQM7890123BR"),
        )
    assert not operational_database.exists()


def test_database_write_failure_rolls_back_whole_replacement(
    operational_database: Path, tmp_path: Path
) -> None:
    files = snapshot(tmp_path)
    with sqlite3.connect(operational_database) as conn:
        before = conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
        conn.execute(
            "CREATE TRIGGER fail_insert BEFORE INSERT ON orders BEGIN SELECT RAISE(ABORT, 'failure'); END"
        )
    with pytest.raises(OperationsImportError):
        import_operations(
            *files,
            operational_database.parent / "operational-catalog.sqlite3",
            operational_database,
        )
    with sqlite3.connect(operational_database) as conn:
        assert (
            conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall() == before
        )
        assert conn.execute("SELECT count(*) FROM customers").fetchone()[0] == 50


def test_order_input_bounds_reject_coercion_and_overflow() -> None:
    for invalid in (True, 0, -1, "1", 2**63):
        with pytest.raises(ValidationError):
            OrderLookupQuery.model_validate({"order_id": invalid})
    for invalid in (True, 0, 21, "5"):
        with pytest.raises(ValidationError):
            OrderListQuery.model_validate({"limit": invalid})


def test_copied_product_references_survive_catalog_changes(
    operational_database: Path,
) -> None:
    repository = SQLiteOrderRepository(operational_database)
    catalog = operational_database.parent / "operational-catalog.sqlite3"
    identity = CustomerIdentity(customer_id=3)
    query = OrderLookupQuery(order_id=1)
    original = repository.get_order(identity, query)
    assert original is not None
    with sqlite3.connect(catalog) as conn:
        conn.execute(
            "UPDATE products SET name = 'Renamed reference', price_centavos = 1 WHERE product_id = 93"
        )
    # Order facts are the operational import, not a join against mutable catalog prices/names.
    assert repository.get_order(identity, query) == original
    import_operations(
        DATA / "operations" / "customers.csv",
        DATA / "operations" / "orders.csv",
        DATA / "operations" / "order_items.csv",
        catalog,
        operational_database,
    )
    refreshed = repository.get_order(identity, query)
    assert refreshed is not None
    assert refreshed.items[0].product_name == "Renamed reference"
    assert refreshed.total_centavos == original.total_centavos
    with sqlite3.connect(catalog) as conn:
        conn.execute("DELETE FROM products WHERE product_id = 93")
    assert repository.get_order(identity, query) == refreshed
