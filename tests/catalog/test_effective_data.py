"""Effective policy and operational contracts motivated by live failures."""

from pathlib import Path

import pytest
from emporio_music.agent.catalog import ProductSearchTool
from emporio_music.domain.catalog import (
    ProductBatchLookupQuery,
    ProductBatchLookupResult,
    ProductSearchQuery,
    ProductSearchResult,
)
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music.paths import DATA_DIRECTORY
from emporio_music.policies.corpus import prepare


def test_preparation_resolves_holiday_scope_and_freight_before_retrieval() -> None:
    corpus = prepare(DATA_DIRECTORY / "policies" / "store_policies.pdf")
    hours = next(c for c in corpus.chunks if c.section == "2")
    assert "Domingos e feriados, com exceções de datas especiais" in hours.text
    assert "Natal, Black Friday e aniversário da loja" in hours.text
    assert "pode haver atendimento" in hours.text
    assert "não confirma abertura nem fechamento" in hours.text
    freight = [c for c in corpus.chunks if c.section.startswith("5.1")]
    assert len(freight) == 1
    assert "igual ou superior a R$ 500,00" in freight[0].text
    assert "acima de R$ 500,00" not in freight[0].text
    assert "policies/freight-clarification.json" in freight[0].source_references
    assert "1 a 3 dias úteis" in freight[0].text


def test_return_rule_is_prepared_with_conditions_and_exclusions() -> None:
    corpus = prepare(DATA_DIRECTORY / "policies" / "store_policies.pdf")
    rule = next(c for c in corpus.chunks if c.section == "4.1").online_return_rule
    assert rule is not None
    assert rule["request_deadline_calendar_days_after_receipt"] == 7
    assert rule["minimum_wait_calendar_days"] == 0
    assert "no_signs_of_use" in rule["required_customer_facts"]
    assert "clearance_explicit_final_sale" in rule["excluded_product_conditions"]


def test_product_id_followup_and_unrestricted_alternatives_use_real_catalog(
    operational_database: Path,
) -> None:
    repository = SQLiteProductRepository(
        operational_database.parent / "operational-catalog.sqlite3"
    )
    tool = ProductSearchTool(repository)
    result = tool.get_product_details(product_id=85, payment_method="standard")
    products = result["products"]
    assert isinstance(products, list)
    assert products[0]["name"] == "Rozini RC-104 Nylon Estudante"
    assert result["total_matches"] == 1
    alternatives = tool.find_product_alternatives(
        product_id=83, payment_method="standard", limit=20
    )
    candidates = alternatives["products"]
    assert isinstance(candidates, list)
    assert candidates
    assert all(p["product_id"] != 83 and p["available"] for p in candidates)
    assert all(p["category_name"] == "Violões" for p in candidates)
    expected = repository.search(
        ProductSearchQuery(category="Violões", exclude_product_id=83, limit=20)
    )
    assert alternatives["total_matches"] == expected.total_matches
    assert [p["product_id"] for p in candidates] == [
        p.product_id for p in expected.products
    ]
    with pytest.raises(TypeError, match="product_name"):
        tool.get_product_details(
            product_name="wrong name",  # type: ignore[call-arg]
            product_id=85,
            payment_method="standard",
        )


def test_pix_promotion_explanation_uses_the_actual_discount_origin(
    operational_database: Path,
) -> None:
    tool = ProductSearchTool(
        SQLiteProductRepository(
            operational_database.parent / "operational-catalog.sqlite3"
        )
    )
    result = tool.get_product_details(product_id=121, payment_method="pix")
    products = result["products"]
    assert isinstance(products, list)
    assert products[0]["pricing"]["final_price_brl"] == "439.20"
    assert (
        products[0]["pricing"]["explanation"]
        == "Promoção de 20%; não há desconto PIX adicional."
    )


def test_alternatives_honor_explicit_pix_payment(operational_database: Path) -> None:
    tool = ProductSearchTool(
        SQLiteProductRepository(
            operational_database.parent / "operational-catalog.sqlite3"
        )
    )
    result = tool.find_product_alternatives(product_id=96, payment_method="pix")
    products = result["products"]
    assert isinstance(products, list)
    assert products
    assert all(product["pricing"]["payment_method"] == "pix" for product in products)
    assert products[0]["product_id"] == 83
    assert products[0]["pricing"]["final_price_brl"] == "408.41"


def test_model_visible_lookup_contracts_separate_names_ids_and_require_payment() -> (
    None
):
    import asyncio

    from emporio_music.agent.catalog import create_catalog_agent
    from emporio_music.agent.settings import AgentSettings
    from emporio_music.domain.chat import ChatRequest
    from emporio_music.domain.conversations import ExecutionContext
    from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        schemas = {
            tool.name: tool.parameters_json_schema for tool in info.function_tools
        }
        for name in (
            "find_product_by_name",
            "get_product_details",
            "search_available_products",
            "find_product_alternatives",
        ):
            assert "payment_method" in schemas[name]["required"]
        assert "product_name" not in schemas["get_product_details"]["properties"]
        assert "product_id" in schemas["get_product_details"]["required"]
        assert "product_id" not in schemas["find_product_by_name"]["properties"]
        assert "product_name" in schemas["find_product_by_name"]["required"]
        return ModelResponse(parts=[TextPart("Olá!")])

    class UnusedRepository:
        def search(self, query: ProductSearchQuery) -> ProductSearchResult:
            raise AssertionError("Schema inspection needs no catalog read")

        def lookup_many(
            self, query: ProductBatchLookupQuery
        ) -> ProductBatchLookupResult:
            raise AssertionError("Schema inspection needs no catalog read")

    agent = create_catalog_agent(
        AgentSettings(), UnusedRepository(), model=FunctionModel(respond)
    )
    asyncio.run(agent.run(ChatRequest(message="Olá"), context=ExecutionContext()))
