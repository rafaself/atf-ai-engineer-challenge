"""Protect paid-run opt-in and authenticity/preservation of captured evidence."""

import asyncio
import sys
from pathlib import Path

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from emporio_music_backend.agent import examples
from emporio_music_backend.agent.catalog import create_catalog_agent
from emporio_music_backend.agent.factory import PydanticAgentExecutor
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.infrastructure.catalog_import import import_catalog
from emporio_music_backend.ports import ProductRepository


def test_recorder_saves_actual_tool_trace_without_claiming_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = Path(__file__).parents[3] / "data"
    database = tmp_path / "catalog.sqlite3"
    import_catalog(data / "products.csv", data / "categories.csv", database)
    monkeypatch.setattr(examples, "SCENARIOS", (("named", "Consulte GD20"),))

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if any(
            isinstance(part, ToolReturnPart)
            for message in messages
            for part in message.parts
        ):
            return ModelResponse(parts=[TextPart("controlled-answer-marker")])
        return ModelResponse(
            parts=[ToolCallPart("search_products", {"product_name": "GD20"})]
        )

    def factory(
        settings: AgentSettings, repository: ProductRepository
    ) -> PydanticAgentExecutor:
        return create_catalog_agent(settings, repository, model=FunctionModel(model))

    monkeypatch.setattr(examples, "create_catalog_agent", factory)
    output = tmp_path / "evidence"
    asyncio.run(examples.record(database, output))
    text = (output / "named.md").read_text()
    assert '"product_name": "GD20"' in text
    assert '"price_centavos": 219900' in text and '"stock_quantity": 5' in text
    assert examples.snapshot_identity(database) in text
    assert "controlled-answer-marker" in text
    assert "pending human grounding and scope review" in text


def test_cli_requires_opt_in_and_preserves_existing_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "not-opened.sqlite3"
    database.touch()
    output = tmp_path / "evidence"
    output.mkdir()
    existing = output / "previous.md"
    existing.write_text("Keep the actual earlier evidence")
    arguments = [
        "recorder",
        "--database",
        str(database),
        "--output-dir",
        str(output),
    ]
    for opts in (arguments, [*arguments, "--live"]):
        monkeypatch.setattr(sys, "argv", opts)
        with pytest.raises(SystemExit) as failure:
            examples.main()
        assert failure.value.code == 2
    assert existing.read_text() == "Keep the actual earlier evidence"
