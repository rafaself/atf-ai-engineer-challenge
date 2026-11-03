"""Typed deterministic product quotes and installment breakdowns."""

from typing import Annotated, Literal, Self

from pydantic import Field, computed_field, model_validator

from emporio_music.domain.base import ContractModel, NonblankText, NonnegativeInt
from emporio_music.domain.pricing import ProductPricing

Centavos = Annotated[NonnegativeInt, Field(le=2**63 - 1)]
QuotePaymentIntent = Literal["compare", "pix", "credit", "split"]
ShippingDestination = Literal["campo_grande_metro", "other_city"]
QuoteCalculationStatus = Literal["complete", "missing_products", "unavailable_products"]
QuoteTotalScope = Literal[
    "merchandise_only",
    "includes_supported_shipping",
    "shipping_unresolved",
    "comparison_only",
    "not_calculated",
]
InstallmentEligibility = Literal["eligible", "policy_ambiguous"]
InstallmentTotalScope = Literal[
    "not_calculated",
    "not_applicable",
    "merchandise_only",
    "includes_supported_shipping",
]
RequestedInstallmentStatus = Literal[
    "not_requested",
    "not_calculated",
    "eligible",
    "policy_ambiguous",
    "below_minimum",
]
InstallmentMinimumRule = Literal[
    "total_at_least_50", "each_at_least_80", "each_at_least_100"
]


def _format_brl(centavos: int) -> str:
    return f"{centavos // 100}.{centavos % 100:02d}"


def _format_optional_brl(centavos: int | None) -> str | None:
    return None if centavos is None else _format_brl(centavos)


class QuoteItemInput(ContractModel):
    product_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
    quantity: Annotated[int, Field(strict=True, ge=1, le=99)]


class QuoteRequest(ContractModel):
    items: Annotated[tuple[QuoteItemInput, ...], Field(min_length=1, max_length=10)]
    payment_intent: QuotePaymentIntent
    requested_installments: Annotated[int, Field(strict=True, ge=1, le=12)] | None = (
        None
    )
    pix_allocation_centavos: Centavos | None = None
    destination: ShippingDestination | None = None

    @model_validator(mode="after")
    def validate_request(self) -> Self:
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("quote items must use distinct product IDs")
        if self.payment_intent == "split":
            if self.destination is not None:
                raise ValueError(
                    "split quotes with shipping are unsupported because tender allocation is unspecified"
                )
        elif self.pix_allocation_centavos is not None:
            raise ValueError("PIX allocation is only valid for a split quote")
        if self.payment_intent == "compare" and self.destination is not None:
            raise ValueError("choose a payment method before calculating shipping")
        if self.payment_intent in {"pix", "compare"} and self.requested_installments:
            raise ValueError(
                "a requested installment count requires credit or split intent"
            )
        return self


class QuoteLine(ContractModel):
    product_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
    product_name: NonblankText
    quantity: Annotated[int, Field(strict=True, ge=1, le=99)]
    stock_quantity: NonnegativeInt
    status: Literal["quoted", "unavailable", "insufficient_stock"]
    original_unit_centavos: Centavos
    standard_pricing: ProductPricing | None = None
    pix_pricing: ProductPricing | None = None
    original_subtotal_centavos: Centavos
    standard_subtotal_centavos: Centavos | None = None
    pix_subtotal_centavos: Centavos | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def original_unit_brl(self) -> str:
        return _format_brl(self.original_unit_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def original_subtotal_brl(self) -> str:
        return _format_brl(self.original_subtotal_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def standard_subtotal_brl(self) -> str | None:
        return _format_optional_brl(self.standard_subtotal_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pix_subtotal_brl(self) -> str | None:
        return _format_optional_brl(self.pix_subtotal_centavos)


class InstallmentPlan(ContractModel):
    count: Annotated[int, Field(strict=True, ge=1, le=12)]
    eligibility: InstallmentEligibility
    amounts_centavos: Annotated[
        tuple[Centavos, ...], Field(min_length=1, max_length=12)
    ]
    total_centavos: Centavos
    minimum_rule: InstallmentMinimumRule

    @model_validator(mode="after")
    def validate_allocation(self) -> Self:
        if len(self.amounts_centavos) != self.count:
            raise ValueError("installment amounts must match the count")
        if sum(self.amounts_centavos) != self.total_centavos:
            raise ValueError("installment amounts must sum to the payable total")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def amounts_brl(self) -> tuple[str, ...]:
        return tuple(_format_brl(amount) for amount in self.amounts_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_brl(self) -> str:
        return _format_brl(self.total_centavos)


class SplitPaymentQuote(ContractModel):
    status: Literal[
        "not_requested",
        "not_calculated",
        "eligible",
        "not_eligible_at_threshold",
        "eligibility_basis_ambiguous",
        "allocation_required",
        "allocation_invalid",
    ] = "not_requested"
    pix_amount_centavos: Centavos | None = None
    credit_amount_centavos: Centavos | None = None
    credit_installment_options: tuple[InstallmentPlan, ...] = ()
    pix_discount_applied: Literal["no", "policy_ambiguous"] | None = None
    policy_source: NonblankText | None = None
    note: NonblankText | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pix_amount_brl(self) -> str | None:
        return _format_optional_brl(self.pix_amount_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def credit_amount_brl(self) -> str | None:
        return _format_optional_brl(self.credit_amount_centavos)


class ShippingQuote(ContractModel):
    status: Literal[
        "not_requested",
        "not_calculated",
        "supported",
        "basis_ambiguous",
        "unsupported_destination",
    ]
    charge_centavos: Centavos | None = None
    policy_source: NonblankText | None = None
    note: NonblankText | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def charge_brl(self) -> str | None:
        return _format_optional_brl(self.charge_centavos)


class QuoteResult(ContractModel):
    payment_intent: QuotePaymentIntent
    calculation_status: QuoteCalculationStatus
    lines: tuple[QuoteLine, ...]
    missing_product_ids: tuple[int, ...] = ()
    unavailable_product_ids: tuple[int, ...] = ()
    insufficient_stock: tuple[tuple[int, int, int], ...] = ()
    original_total_centavos: Centavos | None = None
    standard_total_centavos: Centavos | None = None
    pix_total_centavos: Centavos | None = None
    selected_merchandise_total_centavos: Centavos | None = None
    quoted_total_centavos: Centavos | None = None
    quoted_total_scope: QuoteTotalScope
    selected_installment_options: tuple[InstallmentPlan, ...] = ()
    installment_total_scope: InstallmentTotalScope
    max_installments: Annotated[int, Field(strict=True, ge=1, le=12)] | None = None
    uncertain_max_installments: (
        Annotated[int, Field(strict=True, ge=1, le=12)] | None
    ) = None
    requested_installments: Annotated[int, Field(strict=True, ge=1, le=12)] | None = (
        None
    )
    requested_installment_status: RequestedInstallmentStatus = "not_requested"
    split_payment: SplitPaymentQuote = Field(default_factory=SplitPaymentQuote)
    shipping: ShippingQuote
    policy_notes: tuple[NonblankText, ...] = ()
    pricing_source: NonblankText = "current_simulated_catalog"
    installment_policy_source: NonblankText | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def original_total_brl(self) -> str | None:
        return _format_optional_brl(self.original_total_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def standard_total_brl(self) -> str | None:
        return _format_optional_brl(self.standard_total_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pix_total_brl(self) -> str | None:
        return _format_optional_brl(self.pix_total_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def selected_merchandise_total_brl(self) -> str | None:
        return _format_optional_brl(self.selected_merchandise_total_centavos)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def quoted_total_brl(self) -> str | None:
        return _format_optional_brl(self.quoted_total_centavos)
