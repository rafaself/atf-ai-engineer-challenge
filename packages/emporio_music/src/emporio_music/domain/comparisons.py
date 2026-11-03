"""Typed numeric comparisons for explicitly identified catalog products."""

from typing import Annotated, Literal, Self

from pydantic import Field, computed_field, model_validator

from emporio_music.domain.base import ContractModel, NonblankText, NonnegativeInt
from emporio_music.domain.pricing import PaymentMethod

ComparisonField = Literal["original_price", "payable_price", "stock_quantity"]


def _format_price_brl(field: ComparisonField, centavos: int) -> str | None:
    if field == "stock_quantity":
        return None
    return f"{centavos // 100}.{centavos % 100:02d}"


class ProductComparisonRequest(ContractModel):
    product_ids: Annotated[
        tuple[Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)], ...],
        Field(min_length=2, max_length=10),
    ]
    fields: Annotated[tuple[ComparisonField, ...], Field(min_length=1, max_length=3)]
    payment_method: PaymentMethod

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        if len(set(self.product_ids)) != len(self.product_ids):
            raise ValueError("product IDs must be unique")
        if len(set(self.fields)) != len(self.fields):
            raise ValueError("comparison fields must be unique")
        return self


class ComparisonEntry(ContractModel):
    product_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
    product_name: NonblankText
    field: ComparisonField
    value: NonnegativeInt

    @computed_field  # type: ignore[prop-decorator]
    @property
    def value_brl(self) -> str | None:
        return _format_price_brl(self.field, self.value)


class NumericComparison(ContractModel):
    field: ComparisonField
    ascending: tuple[ComparisonEntry, ...]
    minimum_product_ids: tuple[int, ...]
    maximum_product_ids: tuple[int, ...]
    difference: NonnegativeInt

    @computed_field  # type: ignore[prop-decorator]
    @property
    def difference_brl(self) -> str | None:
        return _format_price_brl(self.field, self.difference)


class ProductComparisonResult(ContractModel):
    status: Literal["complete", "missing_products"]
    payment_method: PaymentMethod
    requested_product_ids: tuple[int, ...]
    missing_product_ids: tuple[int, ...] = ()
    comparisons: tuple[NumericComparison, ...] = ()
    source: NonblankText = "current_simulated_catalog"
