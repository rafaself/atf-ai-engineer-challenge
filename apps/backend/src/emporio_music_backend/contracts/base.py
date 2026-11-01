"""Shared immutable contract base and scalar validation types."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonblankText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1)
]


PositiveInt = Annotated[int, Field(strict=True, gt=0)]


NonnegativeInt = Annotated[int, Field(strict=True, ge=0)]


class ContractModel(BaseModel):
    """Values are immutable and reject undeclared input fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")
