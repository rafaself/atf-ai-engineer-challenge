"""Read-only SQLite implementation of the product repository port."""

import sqlite3
from contextlib import closing
from pathlib import Path

from emporio_music_backend.application.pricing import calculate_pricing
from emporio_music_backend.contracts import (
    ProductSearchQuery,
    ProductSearchResult,
    ProductSummary,
    PromotionOffer,
)
from emporio_music_backend.contracts.errors import ProductRetrievalError
from emporio_music_backend.diagnostics import failure, trace
from emporio_music_backend.infrastructure._catalog import (
    normalize_lookup,
    validate_schema,
)


class SQLiteProductRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()

    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
        query = ProductSearchQuery.model_validate(query)
        trace("catalog.search")
        clauses: list[str] = []
        parameters: list[int | str] = []
        for value, expression in (
            (query.category, "c.normalized_name = ?"),
            (query.product_name, "instr(p.normalized_name, ?) > 0"),
        ):
            if value is not None:
                normalized = normalize_lookup(value)
                if not normalized:
                    clauses.append("0")
                else:
                    clauses.append(expression)
                    parameters.append(normalized)
        if query.available_only:
            clauses.append("p.status = 'active' AND p.stock_quantity > 0")
        where = " AND ".join(clauses) if clauses else "1"
        source = (
            "FROM products p JOIN categories c USING (category_id) "
            "LEFT JOIN promotions m ON m.product_id = p.product_id AND m.is_active = 1 "
            f"WHERE {where}"
        )
        try:
            uri = self.database_path.as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True, autocommit=True)) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("BEGIN")
                validate_schema(connection)
                rows = connection.execute(
                    "SELECT p.product_id, p.category_id, p.name, c.name AS category_name, "
                    "p.price_centavos, p.stock_quantity, p.status, m.promotion_id, "
                    f"m.discount_percent, m.description AS promotion_description {source}",
                    parameters,
                ).fetchall()
                matched: list[ProductSummary] = []
                seen: set[int] = set()
                for row in rows:
                    if row["product_id"] in seen:
                        raise ValueError("Ambiguous active promotion")
                    seen.add(row["product_id"])
                    offer = (
                        PromotionOffer.model_validate(
                            {
                                "promotion_id": row["promotion_id"],
                                "discount_percent": row["discount_percent"],
                                "description": row["promotion_description"],
                            }
                        )
                        if row["promotion_id"] is not None
                        else None
                    )
                    pricing = calculate_pricing(
                        row["price_centavos"],
                        available=row["status"] == "active"
                        and row["stock_quantity"] > 0,
                        payment_method=query.payment_method,
                        promotion=offer,
                    )
                    product = ProductSummary.model_validate(
                        {
                            key: row[key]
                            for key in (
                                "product_id",
                                "category_id",
                                "name",
                                "category_name",
                                "price_centavos",
                                "stock_quantity",
                                "status",
                            )
                        }
                        | {"pricing": pricing}
                    )
                    price = pricing.final_price_centavos
                    if query.promotions_only and pricing.discount_kind != "promotion":
                        continue
                    if (
                        query.min_price_centavos is not None
                        and price < query.min_price_centavos
                    ):
                        continue
                    if (
                        query.max_price_centavos is not None
                        and price > query.max_price_centavos
                    ):
                        continue
                    matched.append(product)
                matched.sort(
                    key=lambda product: (
                        product.pricing.final_price_centavos,
                        product.product_id,
                    )
                )
                total = len(matched)
                products = tuple(matched[: query.limit])
                connection.execute("COMMIT")
                trace("catalog.result", total_matches=total, returned=len(products))
                return ProductSearchResult(products=products, total_matches=total)
        except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
            trace("catalog.failure", **failure(exc))
            raise ProductRetrievalError(
                "Cannot read a compatible catalog snapshot"
            ) from exc
