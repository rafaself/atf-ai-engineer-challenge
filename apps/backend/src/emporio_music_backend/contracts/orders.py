"""Minimal, immutable operational projections; no customer contact information."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, computed_field, model_validator

from emporio_music_backend.contracts.base import (
    ContractModel,
    NonblankText,
    NonnegativeInt,
)

DatabaseId = Annotated[int, Field(strict=True, gt=0, le=2**63 - 1)]
OrderStatus = Literal["delivered", "shipped", "confirmed", "pending", "cancelled"]


class OrderListQuery(ContractModel):
    limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 5


class OrderLookupQuery(ContractModel):
    order_id: DatabaseId


class OrderSummary(ContractModel):
    order_id: DatabaseId
    order_date: date
    status: OrderStatus
    total_centavos: DatabaseId

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_brl(self) -> str:
        return f"{self.total_centavos // 100}.{self.total_centavos % 100:02d}"


class OrderItem(ContractModel):
    product_id: DatabaseId
    product_name: NonblankText
    quantity: DatabaseId


class OrderDetail(OrderSummary):
    tracking_code: NonblankText | None = None
    estimated_delivery: date | None = None
    items: Annotated[tuple[OrderItem, ...], Field(max_length=20)] = ()
    total_items: NonnegativeInt = 0

    @model_validator(mode="after")
    def validate_items(self) -> Self:
        if self.total_items < len(self.items):
            raise ValueError("total_items must include every returned item")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def items_truncated(self) -> bool:
        return self.total_items > len(self.items)


class OrderListResult(ContractModel):
    orders: Annotated[tuple[OrderSummary, ...], Field(max_length=20)] = ()
    total_matches: NonnegativeInt = 0

    @model_validator(mode="after")
    def validate_total(self) -> Self:
        if self.total_matches < len(self.orders):
            raise ValueError("total_matches must include every returned order")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def truncated(self) -> bool:
        return self.total_matches > len(self.orders)
