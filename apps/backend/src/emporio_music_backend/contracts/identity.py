"""Trusted customer identity without transport credentials."""

from typing import Annotated

from pydantic import Field

from emporio_music_backend.contracts.base import ContractModel, PositiveInt


class CustomerIdentity(ContractModel):
    """Identity supplied by a trusted application boundary, never by the model."""

    customer_id: Annotated[PositiveInt, Field(le=2**63 - 1)]
