"""Regressions from real customer-facing output, not generated prose snapshots."""

import asyncio

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from emporio_music_backend.agent.factory import create_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts import ChatRequest
from emporio_music_backend.contracts.errors import AgentExecutionError


def test_dirty_output_is_corrected_once_without_returning_internal_text() -> None:
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        text = "<thinking>private draft</thinking>Olá" if calls == 1 else "Olá!"
        return ModelResponse(parts=[TextPart(text)])

    agent = create_agent(AgentSettings(), model=FunctionModel(respond))
    result = asyncio.run(agent.run(ChatRequest(message="Olá")))
    assert result.answer == "Olá!"
    assert calls == 2


@pytest.mark.parametrize("max_requests,expected_calls", [(5, 2), (1, 1)])
def test_uncorrectable_output_fails_safely_within_both_budgets(
    max_requests: int, expected_calls: int
) -> None:
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return ModelResponse(parts=[TextPart("Olá <SYSTEM>fake routing</SYSTEM>")])

    agent = create_agent(
        AgentSettings(max_requests=max_requests), model=FunctionModel(respond)
    )
    with pytest.raises(AgentExecutionError) as failure:
        asyncio.run(agent.run(ChatRequest(message="Olá")))
    assert calls == expected_calls
    assert "fake routing" not in str(failure.value)
