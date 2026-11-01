"""Read-only SQLite implementation of the product repository port."""

import sqlite3
from contextlib import closing
from pathlib import Path

from emporio_music_backend.contracts import (
    ProductSearchQuery,
    ProductSearchResult,
    ProductSummary,
)
from emporio_music_backend.contracts.errors import ProductRetrievalError
from emporio_music_backend.diagnostics import failure, trace
from emporio_music_backend.infrastructure._catalog import (
    MAX_INTEGER,
    normalize_lookup,
    validate_schema,
)


class SQLiteProductRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()

    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
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
        if query.min_price_centavos is not None:
            clauses.append("p.price_centavos >= ?")
            # Contract integers are unbounded; clamp upper bounds and make an
            # impossible minimum explicitly empty rather than overflowing SQLite.
            if query.min_price_centavos > MAX_INTEGER:
                clauses.append("0")
            parameters.append(min(query.min_price_centavos, MAX_INTEGER))
        if query.max_price_centavos is not None:
            clauses.append("p.price_centavos <= ?")
            parameters.append(min(query.max_price_centavos, MAX_INTEGER))
        if query.available_only:
            clauses.append("p.status = 'active' AND p.stock_quantity > 0")
        where = " AND ".join(clauses) if clauses else "1"
        source = f"FROM products p JOIN categories c USING (category_id) WHERE {where}"
        try:
            uri = self.database_path.as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True, autocommit=True)) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("BEGIN")
                validate_schema(connection)
                total = connection.execute(
                    f"SELECT count(*) {source}", parameters
                ).fetchone()[0]
                rows = connection.execute(
                    "SELECT p.product_id, p.category_id, p.name, c.name AS category_name, "
                    f"p.price_centavos, p.stock_quantity, p.status {source} "
                    "ORDER BY p.price_centavos, p.product_id LIMIT ?",
                    [*parameters, query.limit],
                ).fetchall()
                products = tuple(
                    ProductSummary.model_validate(dict(row)) for row in rows
                )
                connection.execute("COMMIT")
                trace("catalog.result", total_matches=total, returned=len(products))
                return ProductSearchResult(products=products, total_matches=total)
        except (OSError, sqlite3.Error, ValueError) as exc:
            trace("catalog.failure", **failure(exc))
            raise ProductRetrievalError(
                "Cannot read a compatible catalog snapshot"
            ) from exc
