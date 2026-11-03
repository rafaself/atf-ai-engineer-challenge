"""Read-only customer-scoped order boundary."""

from typing import Protocol

from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.orders import (
    OrderDetail,
    OrderListQuery,
    OrderListResult,
    OrderLookupQuery,
)


class OrderRepository(Protocol):
    def list_orders(
        self, identity: CustomerIdentity, query: OrderListQuery
    ) -> OrderListResult:
        """Return only this known customer's bounded, newest-first orders."""
        ...

    def get_order(
        self, identity: CustomerIdentity, query: OrderLookupQuery
    ) -> OrderDetail | None:
        """Return an owned order; unknown and foreign IDs both return None.

        Unknown customers fail authorization. Storage faults never mean no match.
        """
        ...
