"""Read-only, customer-scoped access to the imported operational snapshot."""

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path

from pydantic import TypeAdapter

from emporio_music_backend.contracts import CustomerIdentity
from emporio_music_backend.contracts.errors import (
    AuthenticationError,
    ConfigurationError,
    OperationalRetrievalError,
)
from emporio_music_backend.contracts.orders import (
    DatabaseId,
    OrderDetail,
    OrderItem,
    OrderListQuery,
    OrderListResult,
    OrderLookupQuery,
    OrderSummary,
)
from emporio_music_backend.diagnostics import failure, trace
from emporio_music_backend.infrastructure._operations import validate_schema

_identifier = TypeAdapter(DatabaseId)
_HEADER = "order_id, order_date, status, total_centavos"


class SQLiteOrderRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()
        try:
            with self._snapshot():
                pass
        except OperationalRetrievalError as exc:
            raise ConfigurationError(
                "Import a compatible operational snapshot"
            ) from exc

    @contextmanager
    def _snapshot(self) -> Iterator[sqlite3.Connection]:
        try:
            with closing(
                sqlite3.connect(
                    self.database_path.as_uri() + "?mode=ro",
                    uri=True,
                    autocommit=True,
                    timeout=0,
                )
            ) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("BEGIN")
                validate_schema(connection)
                yield connection
                connection.execute("COMMIT")
        except (OSError, sqlite3.Error, ValueError) as exc:
            trace("operations.failure", **failure(exc))
            raise OperationalRetrievalError(
                "Cannot read the operational snapshot"
            ) from exc

    @staticmethod
    def _customer_id(identity: CustomerIdentity) -> int:
        # Validate even direct callers before SQL binding (including SQLite size).
        return _identifier.validate_python(
            CustomerIdentity.model_validate(identity).customer_id
        )

    @staticmethod
    def _require_customer(connection: sqlite3.Connection, customer_id: int) -> None:
        if (
            connection.execute(
                "SELECT 1 FROM customers WHERE customer_id = ?", (customer_id,)
            ).fetchone()
            is None
        ):
            raise AuthenticationError("Customer identity required")

    def exists(self, identity: CustomerIdentity) -> bool:
        customer_id = self._customer_id(identity)
        with self._snapshot() as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM customers WHERE customer_id = ?", (customer_id,)
                ).fetchone()
                is not None
            )

    def list_orders(
        self, identity: CustomerIdentity, query: OrderListQuery
    ) -> OrderListResult:
        customer_id = self._customer_id(identity)
        validated = OrderListQuery.model_validate(query)
        with self._snapshot() as connection:
            self._require_customer(connection, customer_id)
            total = connection.execute(
                "SELECT count(*) FROM orders WHERE customer_id = ?", (customer_id,)
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT {_HEADER} FROM orders WHERE customer_id = ? "
                "ORDER BY order_date DESC, order_id DESC LIMIT ?",
                (customer_id, validated.limit),
            ).fetchall()
            result = OrderListResult(
                orders=tuple(OrderSummary.model_validate(dict(row)) for row in rows),
                total_matches=total,
            )
            trace("operations.result", total_matches=total, returned=len(rows))
            return result

    def get_order(
        self, identity: CustomerIdentity, query: OrderLookupQuery
    ) -> OrderDetail | None:
        customer_id = self._customer_id(identity)
        validated = OrderLookupQuery.model_validate(query)
        with self._snapshot() as connection:
            self._require_customer(connection, customer_id)
            row = connection.execute(
                f"SELECT {_HEADER}, tracking_code, estimated_delivery FROM orders "
                "WHERE order_id = ? AND customer_id = ?",
                (validated.order_id, customer_id),
            ).fetchone()
            if row is None:
                return None
            # Scope every read independently, including item counts and projections.
            source = "FROM order_items i JOIN orders o USING (order_id) WHERE o.order_id = ? AND o.customer_id = ?"
            params = (validated.order_id, customer_id)
            total = connection.execute(f"SELECT count(*) {source}", params).fetchone()[
                0
            ]
            items = connection.execute(
                "SELECT i.product_id, p.name AS product_name, i.quantity "
                "FROM order_items i JOIN orders o USING (order_id) JOIN products p USING (product_id) "
                "WHERE o.order_id = ? AND o.customer_id = ? ORDER BY i.product_id LIMIT 20",
                params,
            ).fetchall()
            result = OrderDetail.model_validate(
                {
                    **dict(row),
                    "items": tuple(
                        OrderItem.model_validate(dict(item)) for item in items
                    ),
                    "total_items": total,
                }
            )
            trace("operations.result", total_matches=total, returned=len(items))
            return result
