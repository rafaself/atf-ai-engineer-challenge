"""Transport-neutral chat request and response values."""

from typing import Annotated

from pydantic import UUID4, Field, JsonValue, field_validator

from emporio_music_backend.contracts.base import ContractModel, NonblankText


def _session_id_schema(schema: dict[str, JsonValue]) -> None:
    # Omission creates a session, but explicit null must not silently create one.
    schema.pop("default", None)
    schema.pop("anyOf", None)
    schema.update(type="string", format="uuid4")


class ChatRequest(ContractModel):
    message: Annotated[NonblankText, Field(max_length=4000)]
    session_id: UUID4 | None = Field(default=None, json_schema_extra=_session_id_schema)

    @field_validator("session_id", mode="before")
    @classmethod
    def require_identifier_when_supplied(cls, value: object) -> object:
        if value is None:
            raise ValueError("Omit session_id to create a conversation")
        return value


class AgentResponse(ContractModel):
    answer: NonblankText


class ChatResponse(AgentResponse):
    session_id: UUID4
