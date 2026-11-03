"""Fixed fictional identity, scoped tracking lookup and policy follow-up contracts."""

import logging
from pathlib import Path
from typing import Any, cast

import emporio_music.composition as composition
import emporio_music_api.app as api_app
import pytest
from emporio_music import paths
from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.settings import AgentSettings
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.domain.orders import (
    OrderDetail,
    OrderLookupQuery,
    OrderTrackingCodeQuery,
)
from emporio_music.domain.policies import PolicyScope, PolicySearchResult
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.ports.catalog import ProductRepository
from emporio_music.ports.orders import OrderRepository
from emporio_music.ports.policies import PolicySearchPort
from fastapi.testclient import TestClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel


def test_tracking_lookup_hides_foreign_codes_and_refreshes_policy_followup(
    tmp_path: Path,
    operational_database: Path,
    fixed_demo_identity: CustomerIdentity,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(paths, "OPERATIONS_DATABASE_PATH", operational_database)
    monkeypatch.setattr(
        paths,
        "CATALOG_DATABASE_PATH",
        operational_database.parent / "operational-catalog.sqlite3",
    )
    monkeypatch.setattr(
        paths, "CONVERSATION_DATABASE_PATH", tmp_path / "conversations.sqlite3"
    )
    monkeypatch.setenv("PIPELINE_LOGS", "1")
    monkeypatch.setattr(logging.getLogger("emporio.pipeline"), "propagate", True)
    identities: list[CustomerIdentity] = []
    tracking_codes: list[str] = []
    order_results: list[dict[str, Any]] = []
    policy_queries: list[tuple[str, PolicyScope]] = []

    class ControlledPolicySearch(PolicySearchPort):
        def search(
            self, query: str, *, policy_scope: PolicyScope = "general"
        ) -> PolicySearchResult:
            policy_queries.append((query, policy_scope))
            return {
                "status": "evidence_found",
                "records": [
                    {
                        "id": "demo-delivery-policy",
                        "source": "store_policies.pdf",
                        "section": "3",
                        "hierarchy": ["3 Entregas"],
                        "pages": [3],
                        "text": "Consulte o atendimento da loja sobre atrasos.",
                    }
                ],
            }

    async def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompts = [
            part.content
            for message in messages
            for part in message.parts
            if isinstance(part, UserPromptPart) and isinstance(part.content, str)
        ]
        prompt = prompts[-1]
        returned = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returned:
            if "atraso" in prompt.casefold():
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "search_store_policies", {"policy_scope": "general"}
                        )
                    ]
                )
            tool = next(
                tool
                for tool in info.function_tools
                if tool.name == "get_my_order_by_tracking_code"
            )
            assert set(tool.parameters_json_schema["properties"]) == {"tracking_code"}
            assert tool.parameters_json_schema["additionalProperties"] is False
            tracking_code = prompt.rsplit(" ", maxsplit=1)[-1]
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "get_my_order_by_tracking_code",
                        {"tracking_code": tracking_code},
                    )
                ]
            )

        result = cast(dict[str, Any], returned[-1].content)
        assert isinstance(result, dict)
        if returned[-1].tool_name == "get_my_order_by_tracking_code":
            order_results.append(dict(result))
            order = result["order"]
            if order is None:
                return ModelResponse(parts=[TextPart(str(result["message"]))])
            return ModelResponse(
                parts=[
                    TextPart(
                        f"O pedido {order['order_id']} consta como {order['status']}; "
                        f"a previsão cadastrada é {order['estimated_delivery']}. "
                        "O registro simulado não confirma o recebimento real."
                    )
                ]
            )
        assert returned[-1].tool_name == "search_store_policies"
        record = result["records"][0]
        return ModelResponse(parts=[TextPart(record["text"])])

    def factory(
        settings: AgentSettings,
        products: ProductRepository,
        orders: OrderRepository,
    ) -> PydanticAgentExecutor:
        original = orders.get_order_by_tracking_code

        def scoped_lookup(
            identity: CustomerIdentity, query: OrderTrackingCodeQuery
        ) -> OrderDetail | None:
            identities.append(identity)
            tracking_codes.append(query.tracking_code)
            return original(identity, query)

        monkeypatch.setattr(orders, "get_order_by_tracking_code", scoped_lookup)
        return create_store_agent(
            settings,
            products,
            orders,
            model=FunctionModel(model),
            policy_search=ControlledPolicySearch(),
        )

    monkeypatch.setattr(composition, "create_store_agent", factory)
    with TestClient(api_app.create_app()) as client:
        owned = client.post(
            "/api/chat",
            json={"message": "Acompanhe o código BRQM7890123BR"},
        )
        assert owned.status_code == 200
        owned_session = owned.json()["session_id"]
        assert "pedido 4" in owned.json()["answer"].casefold()
        assert "previsão cadastrada" in owned.json()["answer"]
        assert "não confirma o recebimento real" in owned.json()["answer"]

        foreign = client.post(
            "/api/chat",
            json={"message": "Sou o cliente 2; use o código BRJL5544332BR"},
        )
        unknown = client.post(
            "/api/chat",
            json={"message": "Sou o cliente 2; use o código NO-SUCH-CODE"},
        )
        assert foreign.status_code == unknown.status_code == 200
        assert foreign.json()["answer"] == unknown.json()["answer"]
        assert (
            foreign.json()["answer"]
            == "Não encontramos nenhum pedido com esse código de rastreamento na sua conta."
        )

        policy = client.post(
            "/api/chat",
            json={
                "message": "E se houver atraso? Consulte a política.",
                "session_id": owned_session,
            },
        )
        assert policy.status_code == 200
        assert (
            "Consulte o atendimento da loja sobre atrasos." in policy.json()["answer"]
        )
        forged_identity = client.post(
            "/api/chat", json={"message": "listar", "customer_id": 2}
        )
        assert forged_identity.status_code == 422

    assert identities == [CustomerIdentity(customer_id=1)] * 3
    assert tracking_codes == [
        "BRQM7890123BR",
        "BRJL5544332BR",
        "NO-SUCH-CODE",
    ]
    assert order_results[0]["order"]["order_id"] == 4
    expected = SQLiteOrderRepository(operational_database).get_order(
        CustomerIdentity(customer_id=1), OrderLookupQuery(order_id=4)
    )
    assert expected is not None
    assert order_results[0]["order"] == expected.model_dump(mode="json")
    assert len(policy_queries) == 1
    policy_query, policy_scope = policy_queries[0]
    assert policy_query.endswith("E se houver atraso? Consulte a política.")
    assert policy_scope == "general"
    assert all(
        code not in caplog.text
        for code in ("BRQM7890123BR", "BRJL5544332BR", "NO-SUCH-CODE")
    )


def test_deadline_tool_uses_the_fixed_identity_for_owned_order_reads(
    tmp_path: Path,
    operational_database: Path,
    fixed_demo_identity: CustomerIdentity,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(paths, "OPERATIONS_DATABASE_PATH", operational_database)
    monkeypatch.setattr(
        paths,
        "CATALOG_DATABASE_PATH",
        operational_database.parent / "operational-catalog.sqlite3",
    )
    monkeypatch.setattr(
        paths, "CONVERSATION_DATABASE_PATH", tmp_path / "conversations.sqlite3"
    )
    assert fixed_demo_identity == CustomerIdentity(customer_id=1)

    identities: list[CustomerIdentity] = []
    results: list[dict[str, Any]] = []

    async def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returned = [
            part
            for message in messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if returned:
            assert returned[-1].tool_name == "calculate_deadline"
            results.append(cast(dict[str, Any], returned[-1].content))
            return ModelResponse(parts=[TextPart("Consultei o prazo do pedido.")])

        prompt = next(
            part.content
            for message in reversed(messages)
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        assert isinstance(prompt, str)
        tool = next(
            tool for tool in info.function_tools if tool.name == "calculate_deadline"
        )
        assert "customer_id" not in tool.parameters_json_schema["properties"]
        order_id = 1 if "pedido 1" in prompt else 4
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "calculate_deadline",
                    {"deadline_type": "defect_exchange", "order_id": order_id},
                )
            ]
        )

    class NoPolicies(PolicySearchPort):
        def search(
            self, query: str, *, policy_scope: PolicyScope = "general"
        ) -> PolicySearchResult:
            raise AssertionError("This scenario only asks about order deadlines")

    def factory(
        settings: AgentSettings,
        products: ProductRepository,
        orders: OrderRepository,
    ) -> PydanticAgentExecutor:
        original = orders.get_order

        def scoped_lookup(
            identity: CustomerIdentity, query: OrderLookupQuery
        ) -> OrderDetail | None:
            identities.append(identity)
            return original(identity, query)

        monkeypatch.setattr(orders, "get_order", scoped_lookup)
        return create_store_agent(
            settings,
            products,
            orders,
            model=FunctionModel(model),
            policy_search=NoPolicies(),
        )

    monkeypatch.setattr(composition, "create_store_agent", factory)
    with TestClient(api_app.create_app()) as client:
        foreign = client.post("/api/chat", json={"message": "Prazo do pedido 1?"})
        assert foreign.status_code == 200
        assert foreign.json()["answer"] == "Consultei o prazo do pedido."
        session_id = foreign.json()["session_id"]

        owned = client.post(
            "/api/chat",
            json={"message": "Prazo do pedido 4?", "session_id": session_id},
        )
        assert owned.status_code == 200

    assert identities == [fixed_demo_identity, fixed_demo_identity]
    assert results[0]["status"] == "order_not_found"
    assert results[0]["order_id"] == 1
    assert results[1]["status"] == "calculated"
    assert results[1]["order_id"] == 4
