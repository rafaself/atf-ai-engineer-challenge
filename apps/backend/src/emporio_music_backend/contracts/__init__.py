"""Validated, transport-neutral values shared by application and adapters."""

from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

from emporio_music_backend.contracts.errors import (
    AuthenticationError,
    SessionAccessError,
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


class CustomerIdentity(ContractModel):
    """Identity supplied by a trusted application boundary, never by the model."""

    customer_id: PositiveInt


class ConversationSession(ContractModel):
    """Server-created session metadata; its identifier does not grant access."""

    session_id: UUID4 = Field(default_factory=uuid4)
    owner: CustomerIdentity


class ConversationMessage(ContractModel):
    """Application-owned conversational text, never system/tool instructions."""

    role: Literal["user", "assistant"]
    content: NonblankText


class ExecutionContext(ContractModel):
    """Trusted invocation data kept separate from public chat input."""

    identity: CustomerIdentity | None = None
    session: ConversationSession | None = None
    history: tuple[ConversationMessage, ...] = ()

    @model_validator(mode="after")
    def validate_owned_history(self) -> Self:
        if self.session is not None:
            if self.identity is None:
                raise AuthenticationError("Trusted customer identity is required")
            if self.session.owner != self.identity:
                raise SessionAccessError("Conversation session is inaccessible")
        elif self.history:
            raise ValueError("Conversation history requires an owned session")
        if len(self.history) % 2 or any(
            message.role != ("user" if index % 2 == 0 else "assistant")
            for index, message in enumerate(self.history)
        ):
            raise ValueError("History must contain completed user/assistant turns")
        return self


class HistoryLimits(ContractModel):
    max_turns: Annotated[int, Field(strict=True, ge=1, le=20)] = 6
    max_characters: Annotated[int, Field(strict=True, ge=1, le=64000)] = 24000


class ConversationSnapshot(ContractModel):
    session: ConversationSession
    revision: NonnegativeInt
    history: tuple[ConversationMessage, ...] = ()

    @model_validator(mode="after")
    def validate_history(self) -> Self:
        ExecutionContext(
            identity=self.session.owner, session=self.session, history=self.history
        )
        if len(self.history) // 2 > self.revision:
            raise ValueError("History cannot exceed the committed revision")
        return self


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
