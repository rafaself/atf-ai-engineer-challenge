"""Immutable-source ingestion and consequential pricing rules on real SQLite."""

import csv
import sqlite3
from decimal import localcontext
from pathlib import Path

import pytest
from emporio_music.application.pricing import calculate_pricing
from emporio_music.domain.catalog import ProductSearchQuery
from emporio_music.domain.errors import ProductRetrievalError
from emporio_music.domain.pricing import PromotionOffer
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
from pydantic import ValidationError

DATA = Path(__file__).resolve().parents[1] / "data"


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def sources(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    products, categories, promotions, database = (
        tmp_path / name
        for name in (
            "products.csv",
            "categories.csv",
            "promotions.csv",
            "catalog.sqlite3",
        )
    )
    write_csv(
        categories,
        CATEGORY_COLUMNS,
        [{"category_id": "1", "name": "Violões", "description": "Test category"}],
    )
    rows = [
        {
            "product_id": str(n),
            "category_id": "1",
            "name": f"Instrument {n}",
            "description": "Independent test fixture",
            "price_brl": "10.01" if n != 2 else "9.50",
            "stock_quantity": "0" if n == 3 else "3",
            "status": "discontinued"
            if n == 4
            else "coming_soon"
            if n == 5
            else "active",
            "specs": "{}",
            "created_at": "2026-01-01",
        }
        for n in range(1, 6)
    ]
    write_csv(products, PRODUCT_COLUMNS, rows)
    write_csv(
        promotions,
        PROMOTION_COLUMNS,
        [
            {
                "promotion_id": str(n),
                "product_id": str(n),
                "discount_percent": "10" if n == 1 else "50",
                "description": "Fixture campaign",
                "is_active": "0" if n == 2 else "1",
            }
            for n in range(1, 6)
        ],
    )
    return products, categories, promotions, database


@pytest.mark.parametrize(
    ("original", "percentage", "expected"),
    [
        (1, 50, 1),
        (3, 50, 2),
        (10, 5, 10),
        (30, 5, 29),
        (1001, 10, 901),
        (35900, 10, 32310),
        (2**63 - 1, 1, 9131138316486228049),
        (1, 100, 0),
    ],
)
def test_final_price_half_up_is_exact_even_with_low_decimal_precision(
    original: int, percentage: int, expected: int
) -> None:
    offer = PromotionOffer(
        promotion_id=1, discount_percent=percentage, description="Test"
    )
    with localcontext() as ctx:
        ctx.prec = 2
        quote = calculate_pricing(
            original, available=True, payment_method="pix", promotion=offer
        )
    assert quote.final_price_centavos == expected
    assert quote.discount_percent == percentage and quote.discount_kind == "promotion"


def test_promotion_precedes_pix_and_unavailable_products_have_no_discount() -> None:
    offer = PromotionOffer(promotion_id=1, discount_percent=2, description="Test")
    quote = calculate_pricing(
        10000, available=True, payment_method="pix", promotion=offer
    )
    assert quote.final_price_centavos == 9800 and quote.discount_kind == "promotion"
    assert (
        calculate_pricing(
            10000, available=True, payment_method="pix"
        ).final_price_centavos
        == 9500
    )
    assert (
        calculate_pricing(
            10000, available=True, payment_method="standard"
        ).discount_kind
        == "none"
    )
    for method in ("standard", "pix"):
        # Model validation expresses the public literal contract without unsafe type casts.
        query = ProductSearchQuery.model_validate({"payment_method": method})
        unavailable = calculate_pricing(
            10000, available=False, payment_method=query.payment_method, promotion=offer
        )
        assert (
            unavailable.final_price_centavos == 10000
            and unavailable.discount_kind == "none"
        )
        assert unavailable.promotion_id is None


def test_all_original_promotions_are_stored_without_repair_and_quoted_from_snapshot(
    operational_database: Path,
) -> None:
    catalog = operational_database.parent / "operational-catalog.sqlite3"
    with (DATA / "promotions.csv").open(newline="") as stream:
        expected = [
            (
                int(row["promotion_id"]),
                int(row["product_id"]),
                int(row["discount_percent"]),
                row["description"],
                int(row["is_active"]),
            )
            for row in csv.DictReader(stream)
        ]
    with sqlite3.connect(catalog) as conn:
        assert (
            conn.execute("SELECT * FROM promotions ORDER BY promotion_id").fetchall()
            == expected
        )
        assert (
            conn.execute(
                "SELECT price_centavos FROM products WHERE product_id=127"
            ).fetchone()[0]
            == 35900
        )
    repo = SQLiteProductRepository(catalog)
    offers = repo.search(ProductSearchQuery(promotions_only=True, limit=2))
    assert offers.total_matches == 4 and offers.truncated
    assert [
        (p.product_id, p.pricing.final_price_centavos) for p in offers.products
    ] == [(127, 32310), (121, 43920)]
    for payment in ("pix", "standard"):
        result = repo.search(
            ProductSearchQuery.model_validate(
                {"promotions_only": True, "payment_method": payment, "limit": 20}
            )
        )
        assert [
            (p.product_id, p.pricing.final_price_centavos) for p in result.products
        ] == [(127, 32310), (121, 43920), (90, 196718), (94, 551908)]


def test_payable_bounds_ordering_and_inactive_or_unavailable_offers(
    tmp_path: Path,
) -> None:
    paths = sources(tmp_path)
    import_catalog(*paths)
    repo = SQLiteProductRepository(paths[3])
    result = repo.search(ProductSearchQuery(max_price_centavos=950))
    assert [
        (p.product_id, p.price_centavos, p.pricing.final_price_centavos)
        for p in result.products
    ] == [(1, 1001, 901), (2, 950, 950)]
    assert [
        p.product_id
        for p in repo.search(
            ProductSearchQuery(min_price_centavos=901, max_price_centavos=901)
        ).products
    ] == [1]
    assert not repo.search(ProductSearchQuery(max_price_centavos=900)).products
    pix = repo.search(ProductSearchQuery(payment_method="pix", promotions_only=True))
    assert [p.product_id for p in pix.products] == [1]
    details = repo.search(
        ProductSearchQuery(available_only=False, payment_method="pix")
    )
    for p in details.products:
        if not p.available:
            assert (
                p.pricing.discount_kind == "none"
                and p.pricing.final_price_centavos == p.price_centavos
            )
    assert (
        repo.search(
            ProductSearchQuery(product_name="Instrument 2", payment_method="pix")
        )
        .products[0]
        .pricing.final_price_centavos
        == 903
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("promotion_id", "0"),
        ("promotion_id", "9223372036854775808"),
        ("product_id", "9999"),
        ("discount_percent", "0"),
        ("discount_percent", "101"),
        ("discount_percent", "10.5"),
        ("is_active", "true"),
        ("description", " "),
    ],
)
def test_invalid_promotions_preserve_catalog_and_do_not_rewrite_sources(
    tmp_path: Path, field: str, value: str
) -> None:
    paths = sources(tmp_path)
    import_catalog(*paths)
    before = paths[3].read_bytes()
    row = {
        "promotion_id": "1",
        "product_id": "1",
        "discount_percent": "10",
        "description": "Test",
        "is_active": "1",
        field: value,
    }
    write_csv(paths[2], PROMOTION_COLUMNS, [row])
    raw = paths[2].read_bytes()
    with pytest.raises(CatalogImportError):
        import_catalog(*paths)
    assert paths[3].read_bytes() == before and paths[2].read_bytes() == raw


def test_conflicts_bad_structure_and_failed_writes_are_atomic(tmp_path: Path) -> None:
    paths = sources(tmp_path)
    import_catalog(*paths)
    before = paths[3].read_bytes()
    row = {
        "promotion_id": "1",
        "product_id": "1",
        "discount_percent": "10",
        "description": "Test",
        "is_active": "1",
    }
    for records in ([row, row], [row, {**row, "promotion_id": "2"}]):
        write_csv(paths[2], PROMOTION_COLUMNS, records)
        with pytest.raises(CatalogImportError):
            import_catalog(*paths)
        assert paths[3].read_bytes() == before
    paths[2].write_text("promotion_id,product_id\n1,1\n")
    with pytest.raises(CatalogImportError):
        import_catalog(*paths)
    assert paths[3].read_bytes() == before
    write_csv(paths[2], PROMOTION_COLUMNS, [row])
    with sqlite3.connect(paths[3]) as conn:
        old = conn.execute("SELECT * FROM promotions").fetchall()
        conn.execute(
            "CREATE TRIGGER fail_promotion BEFORE INSERT ON promotions BEGIN SELECT RAISE(ABORT, 'blocked'); END"
        )
    with pytest.raises(CatalogImportError):
        import_catalog(*paths)
    with sqlite3.connect(paths[3]) as conn:
        assert conn.execute("SELECT * FROM promotions").fetchall() == old
        assert conn.execute("SELECT count(*) FROM products").fetchone()[0] == 5
        conn.execute("DROP TRIGGER fail_promotion")
    # Empty promotion snapshots remove offers; repeated imports reproduce the same result.
    write_csv(paths[2], PROMOTION_COLUMNS, [])
    import_catalog(*paths)
    repo = SQLiteProductRepository(paths[3])
    expected = repo.search(ProductSearchQuery())
    import_catalog(*paths)
    assert repo.search(ProductSearchQuery()) == expected
    assert not repo.search(ProductSearchQuery(promotions_only=True)).products
    with sqlite3.connect(paths[3]) as conn:
        conn.execute("DROP TABLE promotions")
    with pytest.raises(ProductRetrievalError):
        repo.search(ProductSearchQuery())


def test_import_rejects_source_alias_and_tool_query_coercion(tmp_path: Path) -> None:
    paths = sources(tmp_path)
    alias = tmp_path / "alias.sqlite3"
    alias.hardlink_to(paths[2])
    raw = paths[2].read_bytes()
    with pytest.raises(CatalogImportError):
        import_catalog(paths[0], paths[1], paths[2], alias)
    assert paths[2].read_bytes() == raw
    for payload in (
        {"promotions_only": 1},
        {"promotions_only": "true"},
        {"payment_method": "card"},
    ):
        with pytest.raises(ValidationError):
            ProductSearchQuery.model_validate(payload)
