import asyncio
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from emporio_music.agent.catalog import ProductSearchTool, create_catalog_agent
from emporio_music.agent.settings import AgentSettings
from emporio_music.domain.catalog import (
    ProductSearchQuery,
    ProductSearchResult,
)
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.errors import (
    AgentExecutionError,
    ProductRetrievalError,
)
from emporio_music.infrastructure.catalog_import import import_catalog
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from pydantic import ValidationError
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel


class RecordingRepository:
    def __init__(self) -> None:
        self.query: ProductSearchQuery | None = None

    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
        self.query = query
        return ProductSearchResult()


def test_tool_forwards_exact_money_and_rejects_invalid_input_before_repository() -> (
    None
):
    repository = RecordingRepository()
    tool = ProductSearchTool(repository)
    result = tool.search_available_products(
        category=" Violões ",
        max_price_brl=Decimal("1000.00"),
        min_price_brl=Decimal("0.29"),
        limit=20,
    )
    assert repository.query == ProductSearchQuery(
        category="Violões",
        min_price_centavos=29,
        max_price_centavos=100000,
        available_only=True,
        limit=20,
    )
    assert result["total_matches"] == 0 and result["truncated"] is False
    expected = repository.query
    for amount in (
        Decimal("-1"),
        Decimal("0.001"),
        Decimal("Infinity"),
        Decimal("1e999999"),
    ):
        with pytest.raises(ValidationError):
            tool.search_available_products(max_price_brl=amount)
    for minimum, maximum in ((Decimal("2"), Decimal("1")),):
        with pytest.raises(ValidationError):
            tool.search_available_products(min_price_brl=minimum, max_price_brl=maximum)
    with pytest.raises(ValidationError):
        tool.search_available_products(category=" ")
    with pytest.raises(ValidationError):
        tool.search_available_products(limit=21)
    assert repository.query is expected


@pytest.mark.parametrize("bound", ["minimum", "maximum"])
def test_search_price_bounds_use_the_commercial_limit(bound: str) -> None:
    repository = RecordingRepository()
    tool = ProductSearchTool(repository)
    limit = Decimal("1000000000.00")
    tool.search_available_products(min_price_brl=limit, max_price_brl=limit)
    assert repository.query is not None
    assert repository.query.min_price_centavos == 100000000000
    assert repository.query.max_price_centavos == 100000000000
    expected = repository.query
    with pytest.raises(ValidationError):
        if bound == "minimum":
            tool.search_available_products(min_price_brl=Decimal("1000000000.01"))
        else:
            tool.search_available_products(max_price_brl=Decimal("1000000000.01"))
    assert repository.query is expected


def test_controlled_agent_queries_real_catalog_and_returns_grounded_metadata(
    tmp_path: Path,
) -> None:
    data = Path(__file__).resolve().parents[1] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(
        data / "products.csv",
        data / "categories.csv",
        data / "promotions.csv",
        database,
    )
    repository = SQLiteProductRepository(database)
    observed: list[object] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if any(
            isinstance(part, UserPromptPart) and part.content == "Olá"
            for message in messages
            for part in message.parts
        ):
            return ModelResponse(parts=[TextPart("Olá!")])
        returns = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            assert info.function_tools[0].name == "search_available_products"
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "search_available_products",
                        {"category": "violoes", "max_price_brl": "1000.00"},
                    )
                ]
            )
        observed.append(returns[-1].content)
        return ModelResponse(parts=[TextPart("Veja algumas opções do catálogo.")])

    executor = create_catalog_agent(
        AgentSettings(), repository, model=FunctionModel(respond)
    )
    response = asyncio.run(
        executor.run(
            ChatRequest(message="Quais violões até R$1000?"), context=ExecutionContext()
        )
    )
    assert "12" in response.answer and "seleção" in response.answer
    assert observed and isinstance(observed[0], dict)
    assert observed[0]["total_matches"] == 12 and observed[0]["truncated"] is True
    assert (
        asyncio.run(
            executor.run(ChatRequest(message="Olá"), context=ExecutionContext())
        ).answer
        == "Olá!"
    )
    tool = ProductSearchTool(repository)
    named = tool.get_product_details(product_name="GD20")
    assert named["products"] == [
        repository.search(ProductSearchQuery(product_name="GD20"))
        .products[0]
        .model_dump(mode="json")
        | {"price_brl": "2199.00"}
    ]
    unavailable = tool.get_product_details(product_name="GF-3D")
    assert unavailable["total_matches"] == 1
    assert tool.search_available_products(product_name="GF-3D")["total_matches"] == 0
    assert tool.search_available_products(product_name="nonexistent")["products"] == []


def test_tool_and_agent_do_not_disguise_repository_failure() -> None:
    class BrokenRepository:
        def search(self, query: ProductSearchQuery) -> ProductSearchResult:
            raise ProductRetrievalError("Catalog unavailable")

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart("search_available_products", {"product_name": "GD20"})]
        )

    tool = ProductSearchTool(BrokenRepository())
    with pytest.raises(ProductRetrievalError):
        tool.search_available_products(product_name="GD20")
    executor = create_catalog_agent(
        AgentSettings(), BrokenRepository(), model=FunctionModel(respond)
    )
    with pytest.raises(ProductRetrievalError):
        asyncio.run(
            executor.run(
                ChatRequest(message="Quanto custa o GD20?"), context=ExecutionContext()
            )
        )


def test_money_conversion_does_not_inherit_ambient_decimal_rounding() -> None:
    repository = RecordingRepository()
    with localcontext() as context:
        context.prec = 2
        ProductSearchTool(repository).search_available_products(
            max_price_brl=Decimal("999.99")
        )
    assert repository.query is not None
    assert repository.query.max_price_centavos == 99999


@pytest.mark.parametrize(
    "arguments",
    [
        {"limit": True},
        {"promotions_only": "true"},
        {"payment_method": "credit"},
    ],
)
def test_sdk_tool_validation_rejects_invalid_arguments_before_repository(
    arguments: dict[str, object],
) -> None:
    repository = RecordingRepository()

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[ToolCallPart("search_available_products", arguments)]
        )

    executor = create_catalog_agent(
        AgentSettings(), repository, model=FunctionModel(respond)
    )
    with pytest.raises(AgentExecutionError):
        asyncio.run(
            executor.run(
                ChatRequest(message="Buscar instrumentos"), context=ExecutionContext()
            )
        )
    assert repository.query is None
