"""Validated payment choices, source offers and calculated quotes."""

from typing import Annotated, Literal, Self

from pydantic import Field, computed_field, model_validator

from emporio_music_backend.contracts.base import (
    ContractModel,
    NonblankText,
    NonnegativeInt,
    PositiveInt,
)

PaymentMethod = Literal["standard", "pix"]


class PromotionOffer(ContractModel):
    promotion_id: Annotated[PositiveInt, Field(le=2**63 - 1)]
    discount_percent: Annotated[int, Field(strict=True, ge=1, le=100)]
    description: NonblankText


class ProductPricing(ContractModel):
    payment_method: PaymentMethod
    final_price_centavos: Annotated[NonnegativeInt, Field(le=2**63 - 1)]
    discount_percent: Annotated[int, Field(strict=True, ge=0, le=100)]
    discount_kind: Literal["none", "promotion", "pix"]
    promotion_id: Annotated[PositiveInt, Field(le=2**63 - 1)] | None = None
    promotion_description: NonblankText | None = None

    @model_validator(mode="after")
    def validate_discount(self) -> Self:
        if self.discount_kind == "promotion":
            if (
                self.promotion_id is None
                or self.promotion_description is None
                or self.discount_percent == 0
            ):
                raise ValueError("Promotion pricing requires its source offer")
        elif self.promotion_id is not None or self.promotion_description is not None:
            raise ValueError("Only promotion pricing carries a promotion")
        if self.discount_kind == "none" and self.discount_percent != 0:
            raise ValueError("Undiscounted pricing has no percentage")
        if self.discount_kind == "pix" and (
            self.payment_method != "pix" or self.discount_percent != 5
        ):
            raise ValueError("PIX pricing requires its non-cumulative percentage")
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def final_price_brl(self) -> str:
        return (
            f"{self.final_price_centavos // 100}.{self.final_price_centavos % 100:02d}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def explanation(self) -> str:
        if self.discount_kind == "promotion":
            return (
                f"Promoção de {self.discount_percent}%; não há desconto PIX adicional."
                if self.payment_method == "pix"
                else f"Promoção de {self.discount_percent}%."
            )
        if self.discount_kind == "pix":
            return "Desconto PIX de 5%; sem promoção aplicada."
        return "Preço de tabela, sem desconto aplicado."
