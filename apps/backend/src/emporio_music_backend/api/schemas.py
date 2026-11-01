"""HTTP-only fictional customer selection, excluded from agent input."""

from typing import Annotated

from pydantic import Field

from emporio_music_backend.contracts.base import PositiveInt
from emporio_music_backend.contracts.chat import ChatRequest


class DemoChatRequest(ChatRequest):
    customer_id: Annotated[PositiveInt, Field(le=2**63 - 1)] | None = None
