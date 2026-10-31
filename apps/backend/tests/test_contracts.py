from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from emporio_music_backend.application import ChatServicePort
from emporio_music_backend.contracts import (
    AgentResponse,
    ChatRequest,
    ChatResponse,
    ExecutionContext,
    ProductSearchQuery,
    ProductSearchResult,
    ProductSummary,
)
from emporio_music_backend.ports import AgentExecutor, ProductRepository


def product(
    *,
    status: Literal["active", "discontinued", "coming_soon"] = "active",
    stock: int = 5,
) -> ProductSummary:
    return ProductSummary(
        product_id=95,
        category_id=5,
        name="Takamine GD20",
        category_name="Violões",
        price_centavos=219900,
        stock_quantity=stock,
        status=status,
    )


def test_chat_text_and_owned_response_contracts() -> None:
    assert ChatRequest(message="  Olá!  ").message == "Olá!"
    assert AgentResponse(answer="  Olá!  ").model_dump() == {"answer": "Olá!"}
    assert len(ChatRequest(message="a" * 4000).message) == 4000
    session_id = uuid4()
    assert (
        ChatRequest(message="Continue", session_id=session_id).session_id == session_id
    )
    assert ChatResponse(answer="Saved", session_id=session_id).session_id == session_id
    with pytest.raises(ValidationError):
        ChatResponse.model_validate({"answer": "No successful turn without a session"})


@pytest.mark.parametrize("value", ["", " \n\t", 123, True, None, "a" * 4001])
def test_invalid_messages_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": value})


@pytest.mark.parametrize("value", ["", "  ", 123, None])
def test_invalid_answers_are_rejected(value: object) -> None:
    with pytest.raises(ValidationError):
        AgentResponse.model_validate({"answer": value})


def test_models_forbid_extra_fields_and_mutation() -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"message": "Olá", "session_id": "123"})
    request = ChatRequest(message="Olá")
    with pytest.raises(ValidationError):
        request.message = "Changed"
    result = ProductSearchResult(products=(product(),), total_matches=1)
    with pytest.raises(ValidationError):
        result.products[0].stock_quantity = 100
    assert isinstance(result.products, tuple)


@pytest.mark.parametrize(
    "values",
    [
        {"category": " "},
        {"product_name": ""},
        {"product_name": 1},
        {"min_price_centavos": -1},
        {"max_price_centavos": -1},
        {"min_price_centavos": 100, "max_price_centavos": 99},
        {"min_price_centavos": True},
        {"max_price_centavos": 1.5},
        {"max_price_centavos": "1000"},
        {"limit": 0},
        {"limit": 21},
        {"limit": True},
        {"limit": 1.5},
        {"available_only": "false"},
        {"sql": "SELECT * FROM products"},
    ],
)
def test_invalid_search_inputs_are_rejected(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProductSearchQuery.model_validate(values)


def test_search_defaults_and_inclusive_equal_bounds() -> None:
    query = ProductSearchQuery()
    assert query.available_only is True
    assert query.limit == 10
    assert query.category is None and query.product_name is None
    query = ProductSearchQuery(
        category=" Violões ",
        product_name=" Takamine ",
        min_price_centavos=0,
        max_price_centavos=0,
        available_only=False,
        limit=20,
    )
    assert query.category == "Violões" and query.product_name == "Takamine"
    assert query.min_price_centavos == query.max_price_centavos == 0
    assert not query.available_only
    assert ProductSearchQuery(limit=1).limit == 1


@pytest.mark.parametrize(
    ("status", "stock", "available"),
    [
        ("active", 5, True),
        ("active", 0, False),
        ("discontinued", 5, False),
        ("coming_soon", 5, False),
    ],
)
def test_availability_is_derived(
    status: Literal["active", "discontinued", "coming_soon"],
    stock: int,
    available: bool,
) -> None:
    item = product(status=status, stock=stock)
    assert item.available is available
    assert item.model_dump()["available"] is available


@pytest.mark.parametrize(
    "changes",
    [
        {"product_id": 0},
        {"category_id": -1},
        {"product_id": True},
        {"category_id": 1.5},
        {"name": " "},
        {"category_name": ""},
        {"price_centavos": 0},
        {"price_centavos": 2199.9},
        {"stock_quantity": -1},
        {"stock_quantity": False},
        {"status": "unknown"},
        {"available": True},
    ],
)
def test_invalid_product_output_is_rejected(changes: dict[str, object]) -> None:
    values = product().model_dump(exclude_computed_fields=True)
    with pytest.raises(ValidationError):
        ProductSummary.model_validate(values | changes)


def test_empty_complete_and_truncated_results() -> None:
    empty = ProductSearchResult()
    assert empty.products == () and empty.total_matches == 0
    assert not empty.truncated
    complete = ProductSearchResult(products=(product(),), total_matches=1)
    assert not complete.truncated
    limited = ProductSearchResult(products=(product(),), total_matches=12)
    assert limited.truncated
    output = limited.model_dump(mode="json")
    assert output["truncated"] is True
    assert output["products"][0]["price_centavos"] == 219900
    with pytest.raises(ValidationError):
        ProductSearchResult(products=(product(),), total_matches=0)
    for invalid in (-1, True, 1.5):
        with pytest.raises(ValidationError):
            ProductSearchResult.model_validate({"total_matches": invalid})


class FakeAgent:
    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        return AgentResponse(answer=request.message)


class FakeRepository:
    """Canned results demonstrate substitution without implementing filtering."""

    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
        return ProductSearchResult(products=(product(),), total_matches=1)


class FakeChatService:
    async def chat(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> ChatResponse:
        return ChatResponse(
            answer=request.message, session_id=request.session_id or uuid4()
        )


# Structural compatibility is a static guarantee; executing these canned fakes
# would only test their own pass-through bodies, not application behavior.
if TYPE_CHECKING:
    agent: AgentExecutor = FakeAgent()
    service: ChatServicePort = FakeChatService()
    repository: ProductRepository = FakeRepository()
