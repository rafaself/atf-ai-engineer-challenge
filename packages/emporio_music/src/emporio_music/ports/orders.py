"""Read-only customer-scoped order boundary."""

from typing import Protocol

from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.orders import (
    OrderDetail,
    OrderListQuery,
    OrderListResult,
    OrderLookupQuery,
    OrderTrackingCodeQuery,
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

    def get_order_by_tracking_code(
        self, identity: CustomerIdentity, query: OrderTrackingCodeQuery
    ) -> OrderDetail | None:
        """Return one exact owned match; foreign and unknown codes both return None.

        More than one owned match raises AmbiguousTrackingCodeError. Unknown
        customers and storage faults remain distinct from a code that has no match.
        """
        ...
