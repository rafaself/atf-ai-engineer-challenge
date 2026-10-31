"""Validated, transport-neutral values shared by application and adapters."""

from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    computed_field,
    model_validator,
)

NonblankText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]
NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]
ProductStatus = Literal["active", "discontinued", "coming_soon"]


class ContractModel(BaseModel):
    """Values are immutable and reject undeclared input fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ChatRequest(ContractModel):
    message: Annotated[NonblankText, Field(max_length=4000)]


class ChatResponse(ContractModel):
    answer: NonblankText


class ProductSearchQuery(ContractModel):
    """Inclusive centavo bounds; textual filters combine with AND.

    Repositories normalize case/accents and match names by literal substring.
    Unknown filters yield no matches, never an unrestricted search. Results are
    ordered by price ascending, then product ID. Named queries can explicitly
    disable available_only to inspect unavailable catalog entries.
    """

    category: NonblankText | None = None
    product_name: NonblankText | None = None
    min_price_centavos: NonnegativeInt | None = None
    max_price_centavos: NonnegativeInt | None = None
    available_only: StrictBool = True
    limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10

    @model_validator(mode="after")
    def validate_price_range(self) -> Self:
        if (
            self.min_price_centavos is not None
            and self.max_price_centavos is not None
            and self.min_price_centavos > self.max_price_centavos
        ):
            raise ValueError("minimum price must not exceed maximum price")
        return self


class ProductSummary(ContractModel):
    product_id: PositiveInt
    category_id: PositiveInt
    name: NonblankText
    category_name: NonblankText
    price_centavos: PositiveInt
    stock_quantity: NonnegativeInt
    status: ProductStatus

    @computed_field  # type: ignore[prop-decorator]  # mypy cannot type decorated properties.
    @property
    def available(self) -> bool:
        return self.status == "active" and self.stock_quantity > 0


class ProductSearchResult(ContractModel):
    products: tuple[ProductSummary, ...] = ()
    total_matches: NonnegativeInt = 0

    @model_validator(mode="after")
    def validate_total(self) -> Self:
        if self.total_matches < len(self.products):
            raise ValueError("total_matches must include every returned product")
        return self

    @computed_field  # type: ignore[prop-decorator]  # mypy cannot type decorated properties.
    @property
    def truncated(self) -> bool:
        return self.total_matches > len(self.products)
