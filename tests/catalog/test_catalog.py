import csv
import hashlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from emporio_music.domain.catalog import ProductSearchQuery
from emporio_music.domain.errors import ProductRetrievalError
from emporio_music.infrastructure.catalog_import import (
    CATEGORY_COLUMNS,
    PRODUCT_COLUMNS,
    PROMOTION_COLUMNS,
    CatalogImportError,
    import_catalog,
)
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music.ports.catalog import ProductRepository

from tests._support import REPOSITORY_ROOT


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def item(identifier: int = 1, /, **changes: str) -> dict[str, str]:
    return {
        "product_id": str(identifier),
        "category_id": "1",
        "name": "Violão Árvore",
        "description": "Private description not for validation diagnostics",
        "price_brl": "10.10",
        "stock_quantity": "2",
        "status": "active",
        "specs": '{"strings":"nylon"}',
        "created_at": "2025-06-01",
        **changes,
    }


def sources(
    tmp_path: Path, rows: list[dict[str, str]] | None = None
) -> tuple[Path, Path, Path]:
    products, categories, database = (
        tmp_path / name
        for name in ("products.csv", "categories.csv", "catalog.sqlite3")
    )
    write_csv(
        categories,
        CATEGORY_COLUMNS,
        [
            {"category_id": "1", "name": "Violões", "description": "Guitars"},
            {"category_id": "2", "name": "Ukuleles", "description": "Ukuleles"},
        ],
    )
    write_csv(products, PRODUCT_COLUMNS, rows if rows is not None else [item()])
    write_csv(tmp_path / "promotions.csv", PROMOTION_COLUMNS, [])
    return products, categories, database


def test_supplied_snapshot_and_grounded_searches(tmp_path: Path) -> None:
    data = REPOSITORY_ROOT / "data"
    products, categories = (
        data / "catalog" / "products.csv",
        data / "catalog" / "categories.csv",
    )
    hashes = [
        hashlib.sha256(path.read_bytes()).digest() for path in (products, categories)
    ]
    database = tmp_path / "catalog.sqlite3"
    report = import_catalog(
        products, categories, data / "catalog" / "promotions.csv", database
    )
    assert (report.products, report.categories) == (65, 9)
    repository: ProductRepository = SQLiteProductRepository(database)
    budget = repository.search(
        ProductSearchQuery(category="VIoloes", max_price_centavos=100000)
    )
    assert (
        budget.total_matches == 12 and len(budget.products) == 10 and budget.truncated
    )
    all_matches = repository.search(
        ProductSearchQuery(category="Violões", max_price_centavos=100000, limit=20)
    )
    assert len(all_matches.products) == 12 and not all_matches.truncated
    takamine = repository.search(ProductSearchQuery(product_name="takamine gd20"))
    assert takamine.total_matches == 1
    assert (
        takamine.products[0].price_centavos,
        takamine.products[0].stock_quantity,
    ) == (219900, 5)
    assert not repository.search(ProductSearchQuery(product_name="GF-3D")).products
    unavailable = repository.search(
        ProductSearchQuery(product_name="GF-3D", available_only=False)
    )
    assert unavailable.total_matches == 1 and not unavailable.products[0].available
    assert [
        hashlib.sha256(path.read_bytes()).digest() for path in (products, categories)
    ] == hashes


def test_search_order_can_descend_by_payable_price_with_stable_id_ties(
    tmp_path: Path,
) -> None:
    products, categories, database = sources(
        tmp_path,
        [
            item(3, price_brl="20.00"),
            item(2, price_brl="20.00"),
            item(1, price_brl="10.00"),
        ],
    )
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    repository = SQLiteProductRepository(database)

    descending = repository.search(
        ProductSearchQuery(sort_order="price_desc", limit=20)
    )
    ascending = repository.search(ProductSearchQuery(limit=20))

    assert [product.product_id for product in descending.products] == [2, 3, 1]
    assert [product.product_id for product in ascending.products] == [1, 2, 3]


def test_reimport_replaces_snapshot_and_removes_absent_categories(
    tmp_path: Path,
) -> None:
    products, categories, database = sources(
        tmp_path, [item(), item(2, category_id="2")]
    )
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    before = database.read_bytes()
    expected = SQLiteProductRepository(database).search(ProductSearchQuery())
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    repository = SQLiteProductRepository(database)
    assert repository.search(ProductSearchQuery()) == expected
    write_csv(products, PRODUCT_COLUMNS, [item(price_brl="11.99", stock_quantity="0")])
    write_csv(
        categories,
        CATEGORY_COLUMNS,
        [{"category_id": "1", "name": "Violões", "description": "Guitars"}],
    )
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    result = repository.search(ProductSearchQuery(available_only=False))
    assert result.total_matches == 1 and result.products[0].price_centavos == 1199
    assert result.products[0].stock_quantity == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM categories").fetchone()[0] == 1
    assert database.read_bytes() != before


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("product_id", "0"),
        ("product_id", "1.5"),
        ("product_id", str(2**63)),
        ("category_id", "99"),
        ("name", " "),
        ("name", "\u0301"),
        ("description", ""),
        ("stock_quantity", "-1"),
        ("stock_quantity", "true"),
        ("stock_quantity", "1.1"),
        ("stock_quantity", str(2**63)),
        ("price_brl", "0"),
        ("price_brl", "-1"),
        ("price_brl", "NaN"),
        ("price_brl", "Infinity"),
        ("price_brl", "0.001"),
        ("price_brl", "1e-1000000000"),
        ("price_brl", "92233720368547758.08"),
        ("price_brl", "1.00000000000000000000000000000000000001"),
        ("status", "unknown"),
        ("created_at", "2025-02-30"),
        ("created_at", "20250601"),
        ("specs", "[]"),
        ("specs", "null"),
        ("specs", "invalid"),
        ("specs", '{"bad":NaN}'),
        ("specs", '{"x":1e9999999999999999999}'),
    ],
)
def test_invalid_product_preserves_last_snapshot(
    tmp_path: Path, field: str, value: str
) -> None:
    products, categories, database = sources(tmp_path)
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    before = database.read_bytes()
    write_csv(products, PRODUCT_COLUMNS, [item(**{field: value})])
    with pytest.raises(CatalogImportError) as error:
        import_catalog(products, categories, tmp_path / "promotions.csv", database)
    assert f"products.csv:2: {field}:" in str(error.value)
    assert "Private description" not in str(error.value)
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "content",
    [
        "",
        "product_id,product_id\n1,1\n",
        "product_id\n1\n",
        ",".join(PRODUCT_COLUMNS) + "\n1,2\n",
        ",".join(PRODUCT_COLUMNS) + "\n",
        ",".join(PRODUCT_COLUMNS) + '\n"unterminated',
    ],
)
def test_bad_csv_does_not_create_database(tmp_path: Path, content: str) -> None:
    products, categories, database = sources(tmp_path)
    products.write_text(content)
    with pytest.raises(CatalogImportError):
        import_catalog(products, categories, tmp_path / "promotions.csv", database)
    assert not database.exists()


def test_duplicate_products_and_invalid_category_inputs(tmp_path: Path) -> None:
    products, categories, database = sources(tmp_path, [item(), item()])
    with pytest.raises(CatalogImportError, match="product_id: duplicate"):
        import_catalog(products, categories, tmp_path / "promotions.csv", database)
    write_csv(products, PRODUCT_COLUMNS, [item()])
    for duplicate in (
        {"category_id": "1", "name": "Other", "description": "Other"},
        {"category_id": "2", "name": "VIOLOES", "description": "Other"},
        {"category_id": "2", "name": "\u0301", "description": "Other"},
        {"category_id": "2", "name": "Other", "description": " "},
    ):
        write_csv(
            categories,
            CATEGORY_COLUMNS,
            [
                {"category_id": "1", "name": "Violões", "description": "Guitars"},
                duplicate,
            ],
        )
        with pytest.raises(CatalogImportError):
            import_catalog(products, categories, tmp_path / "promotions.csv", database)
    assert not database.exists()


def test_database_write_failure_rolls_back_deletions(tmp_path: Path) -> None:
    products, categories, database = sources(tmp_path)
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER fail_insert BEFORE INSERT ON products BEGIN SELECT RAISE(ABORT, 'blocked write'); END"
        )
    write_csv(products, PRODUCT_COLUMNS, [item(2)])
    with pytest.raises(CatalogImportError, match="blocked write") as error:
        import_catalog(products, categories, tmp_path / "promotions.csv", database)
    assert isinstance(error.value.__cause__, sqlite3.Error)
    result = SQLiteProductRepository(database).search(ProductSearchQuery())
    assert result.products[0].product_id == 1 and result.total_matches == 1


def test_schema_constraints_enforce_catalog_integrity(tmp_path: Path) -> None:
    products, categories, database = sources(tmp_path)
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for statement in (
            "UPDATE products SET price_centavos = 'bad'",
            "UPDATE products SET stock_quantity = 1.5",
            "UPDATE products SET stock_quantity = -1",
            "UPDATE products SET status = 'bad'",
            "UPDATE products SET category_id = 99",
            "UPDATE products SET name = ''",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(statement)


@pytest.mark.parametrize(
    "setup",
    [
        "PRAGMA user_version=2",
        "CREATE TABLE unrelated (value TEXT)",
        "CREATE TABLE sqlitefoo (value TEXT)",
        "CREATE TABLE categories (category_id INTEGER); PRAGMA user_version=1",
    ],
)
def test_incompatible_database_is_unchanged(tmp_path: Path, setup: str) -> None:
    products, categories, database = sources(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.executescript(setup)
    before = database.read_bytes()
    with pytest.raises(CatalogImportError, match="compatible"):
        import_catalog(products, categories, tmp_path / "promotions.csv", database)
    with pytest.raises(ProductRetrievalError):
        SQLiteProductRepository(database).search(ProductSearchQuery())
    assert database.read_bytes() == before


def test_filters_literals_order_bounds_and_unavailable_statuses(tmp_path: Path) -> None:
    rows = [
        item(3),
        item(1),
        item(2, name="Árvore 100%_\\'"),
        item(4, category_id="2"),
        item(5, status="discontinued"),
        item(6, status="coming_soon"),
        item(7, stock_quantity="0"),
    ]
    products, categories, database = sources(tmp_path, rows)
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    repository = SQLiteProductRepository(database)
    limited = repository.search(
        ProductSearchQuery(
            category="VIOLOES",
            product_name="arvore",
            min_price_centavos=1010,
            max_price_centavos=1010,
            limit=2,
        )
    )
    assert [row.product_id for row in limited.products] == [1, 2]
    assert limited.total_matches == 3 and limited.truncated
    assert (
        repository.search(ProductSearchQuery(product_name="%_\\'"))
        .products[0]
        .product_id
        == 2
    )
    for query in (
        ProductSearchQuery(category="missing"),
        ProductSearchQuery(product_name="' OR 1=1 --"),
        ProductSearchQuery(category="\u0301"),
        ProductSearchQuery(product_name="\u0301"),
        ProductSearchQuery(max_price_centavos=1009),
        ProductSearchQuery(min_price_centavos=1011),
        ProductSearchQuery(min_price_centavos=2**100),
    ):
        assert repository.search(query).total_matches == 0
    all_products = repository.search(
        ProductSearchQuery(available_only=False, max_price_centavos=2**100)
    )
    assert all_products.total_matches == 7
    assert [row.product_id for row in all_products.products if not row.available] == [
        5,
        6,
        7,
    ]


def test_money_is_exact_and_missing_database_is_not_created(tmp_path: Path) -> None:
    products, categories, database = sources(tmp_path, [item(price_brl="0.2900")])
    with pytest.raises(ProductRetrievalError) as error:
        SQLiteProductRepository(database).search(ProductSearchQuery())
    assert isinstance(error.value.__cause__, sqlite3.Error) and not database.exists()
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    assert (
        SQLiteProductRepository(database)
        .search(ProductSearchQuery())
        .products[0]
        .price_centavos
        == 29
    )
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA ignore_check_constraints = ON")
        connection.execute("UPDATE products SET status='invalid'")
    with pytest.raises(ProductRetrievalError) as invalid:
        SQLiteProductRepository(database).search(
            ProductSearchQuery(available_only=False)
        )
    assert isinstance(invalid.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("invalid_specs", "diagnostic"),
    [
        (None, "products.csv:1: header"),
        ('{"x":1e9999999999999999999}', "products.csv:2: specs"),
    ],
)
def test_import_module_command_paths_and_exits(
    tmp_path: Path, project_copy: Path, invalid_specs: str | None, diagnostic: str
) -> None:
    products, categories, _ = sources(project_copy / "data")
    database = project_copy / "data" / "catalog" / "catalog.sqlite3"
    command = [
        sys.executable,
        "-m",
        "emporio_music.infrastructure.catalog_import",
        "--products",
        str(products),
        "--categories",
        str(categories),
        "--promotions",
        str(products.parent / "promotions.csv"),
    ]
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    environment["PYTHONPATH"] = str(project_copy / "packages/emporio_music/src")
    environment["EMPORIO_MUSIC_DATA_DIR"] = str(project_copy / "data")
    success = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert success.returncode == 0 and "2 categories and 1 products" in success.stdout
    if invalid_specs is None:
        products.write_text("bad header\n")
    else:
        write_csv(products, PRODUCT_COLUMNS, [item(specs=invalid_specs)])
    failure = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert failure.returncode == 1 and diagnostic in failure.stderr
    assert "Traceback" not in failure.stderr
    assert (
        SQLiteProductRepository(database).search(ProductSearchQuery()).total_matches
        == 1
    )


@pytest.mark.parametrize(
    ("price", "cents"),
    [
        ("0.01", 1),
        ("10e0", 1000),
        ("92233720368547758.07", 9223372036854775807),
    ],
)
def test_exact_price_edges(tmp_path: Path, price: str, cents: int) -> None:
    products, categories, database = sources(tmp_path, [item(price_brl=price)])
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    assert (
        SQLiteProductRepository(database)
        .search(ProductSearchQuery())
        .products[0]
        .price_centavos
        == cents
    )


def test_count_and_rows_share_snapshot_during_concurrent_import(tmp_path: Path) -> None:
    products, categories, database = sources(tmp_path, [item(), item(2)])
    import_catalog(products, categories, tmp_path / "promotions.csv", database)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
    reader = sqlite3.connect(
        database.resolve().as_uri() + "?mode=ro", uri=True, autocommit=True
    )
    # The repository still opens read-only connections normally; this hook only
    # schedules a second real transaction after schema validation, before product projection.
    changed = False

    write_csv(products, PRODUCT_COLUMNS, [item()])
    # Patch only the repository's connection acquisition, not the SQLite module
    # used by the concurrent importer, by returning the reader once then delegating.
    original_connect = sqlite3.connect
    with patch("sqlite3.connect", side_effect=[reader]) as mocked:

        def replace_after_count(statement: str) -> None:
            nonlocal changed
            if statement.startswith("SELECT p.product_id") and not changed:
                changed = True
                mocked.side_effect = original_connect
                import_catalog(
                    products, categories, tmp_path / "promotions.csv", database
                )

        reader.set_trace_callback(replace_after_count)
        snapshot = SQLiteProductRepository(database).search(ProductSearchQuery())
    assert changed
    assert snapshot.total_matches == len(snapshot.products) == 2
    assert (
        SQLiteProductRepository(database).search(ProductSearchQuery()).total_matches
        == 1
    )
