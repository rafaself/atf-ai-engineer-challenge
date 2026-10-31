import asyncio
import subprocess
import sys

import pytest
from pydantic_ai import Tool
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from emporio_music_backend.agent.factory import create_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts import ChatRequest
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    ConfigurationError,
    ProviderUnavailableError,
)
from emporio_music_backend.ports import AgentExecutor


def test_controlled_tool_round_trip_and_stateless_runs() -> None:
    calls: list[str] = []

    def echo_code(code: str) -> str:
        """Return the supplied verification code."""
        calls.append(code)
        return code

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not any(
            isinstance(part, ToolReturnPart)
            for message in messages
            for part in message.parts
        ):
            assert info.function_tools[0].name == "echo_code"
            return ModelResponse(parts=[ToolCallPart("echo_code", {"code": "checked"})])
        return ModelResponse(parts=[TextPart("Verificado: checked")])

    executor: AgentExecutor = create_agent(
        AgentSettings(), model=FunctionModel(respond), tools=[Tool(echo_code)]
    )
    for _ in range(2):
        assert (
            asyncio.run(executor.run(ChatRequest(message="Verifique o código"))).answer
            == "Verificado: checked"
        )
    assert calls == ["checked", "checked"]


def test_provider_failure_is_explicit_and_sanitized() -> None:
    def fail(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise ModelHTTPError(503, "test", {"detail": "private provider body"})

    executor = create_agent(AgentSettings(), model=FunctionModel(fail))
    with pytest.raises(ProviderUnavailableError) as error:
        asyncio.run(executor.run(ChatRequest(message="Olá")))
    assert "private" not in str(error.value) and error.value.__cause__ is not None


@pytest.mark.parametrize(
    ("max_requests", "max_tool_calls", "expected_requests", "expected_tools"),
    [(2, 5, 2, 2), (5, 1, 2, 1)],
    ids=["request-cap", "tool-call-cap"],
)
def test_independent_budgets_stop_model_loop(
    max_requests: int, max_tool_calls: int, expected_requests: int, expected_tools: int
) -> None:
    requests = 0
    tools = 0

    def echo() -> str:
        nonlocal tools
        tools += 1
        return "ok"

    def repeat(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal requests
        requests += 1
        return ModelResponse(parts=[ToolCallPart("echo", {})])

    executor = create_agent(
        AgentSettings(max_requests=max_requests, max_tool_calls=max_tool_calls),
        model=FunctionModel(repeat),
        tools=[Tool(echo)],
    )
    with pytest.raises(AgentExecutionError):
        asyncio.run(executor.run(ChatRequest(message="continue")))
    assert requests == expected_requests
    assert tools == expected_tools


def test_configuration_and_placeholder_profile_do_not_require_credentials() -> None:
    settings = AgentSettings.from_environment(
        {"AWS_PROFILE": "configure-project-profile", "AWS_REGION": "us-east-1"}
    )
    assert settings.aws_profile == "configure-project-profile"
    with pytest.raises(ConfigurationError):
        create_agent(settings)
    with pytest.raises(ConfigurationError):
        AgentSettings.from_environment({"AGENT_MAX_REQUESTS": "0"})
    with pytest.raises(ConfigurationError):
        AgentSettings.from_environment({"BEDROCK_MODEL_ID": " "})


def test_live_probe_requires_explicit_opt_in() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "emporio_music_backend.agent.smoke"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 2 and "--live is required" in result.stderr
    assert not result.stdout
