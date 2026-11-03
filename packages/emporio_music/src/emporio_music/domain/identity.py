"""Selected fictional customer scope, without credentials."""

from typing import Annotated

from pydantic import Field

from emporio_music.domain.base import ContractModel, PositiveInt


class CustomerIdentity(ContractModel):
    """Customer scope supplied by the application boundary, never by the model."""

    customer_id: Annotated[PositiveInt, Field(le=2**63 - 1)]
