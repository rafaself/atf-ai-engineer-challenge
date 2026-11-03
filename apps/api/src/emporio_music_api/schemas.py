"""HTTP-only fictional customer selection, excluded from agent input."""

from typing import Annotated

from emporio_music.domain.base import PositiveInt
from emporio_music.domain.chat import ChatRequest
from pydantic import Field


class DemoChatRequest(ChatRequest):
    customer_id: Annotated[PositiveInt, Field(le=2**63 - 1)] | None = None
