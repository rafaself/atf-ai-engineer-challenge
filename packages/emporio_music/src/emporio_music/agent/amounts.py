"""Validated BRL tool inputs converted exactly to integer centavos."""

from decimal import Decimal, localcontext
from typing import Annotated

from pydantic import Field, TypeAdapter

BRLAmount = Annotated[
    Decimal,
    Field(
        ge=0,
        le=Decimal("1000000000"),
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
    ),
]
_amount = TypeAdapter(BRLAmount)


def brl_to_centavos(value: Decimal | None) -> int | None:
    if value is None:
        return None
    amount = _amount.validate_python(value)
    with localcontext() as context:
        context.prec = 21
        return int(amount * 100)
