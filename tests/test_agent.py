import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from emporio_music.agent.factory import create_agent
from emporio_music.agent.settings import AgentSettings, load_agent_settings
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.errors import (
    AgentExecutionError,
    ConfigurationError,
    ProviderUnavailableError,
)
from emporio_music.ports.agent import AgentExecutor
from pydantic import ValidationError
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
            asyncio.run(
                executor.run(
                    ChatRequest(message="Verifique o código"),
                    context=ExecutionContext(),
                )
            ).answer
            == "Verificado: checked"
        )
    assert calls == ["checked", "checked"]


def test_provider_failure_is_explicit_and_sanitized() -> None:
    def fail(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise ModelHTTPError(503, "test", {"detail": "private provider body"})

    executor = create_agent(AgentSettings(), model=FunctionModel(fail))
    with pytest.raises(ProviderUnavailableError) as error:
        asyncio.run(
            executor.run(ChatRequest(message="Olá"), context=ExecutionContext())
        )
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
        asyncio.run(
            executor.run(ChatRequest(message="continue"), context=ExecutionContext())
        )
    assert requests == expected_requests
    assert tools == expected_tools


def test_environment_settings_load_and_explicit_values_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "BEDROCK_MODEL_ID": "configured-model",
        "AWS_PROFILE": "configure-project-profile",
        "AWS_DEFAULT_REGION": "sa-east-1",
        "AWS_REGION": "us-east-1",
        "AGENT_MAX_REQUESTS": "3",
        "AGENT_MAX_TOOL_CALLS": "4",
        "AGENT_MAX_OUTPUT_TOKENS": "512",
        "AGENT_REQUEST_TIMEOUT_SECONDS": "12.5",
    }.items():
        monkeypatch.setenv(name, value)

    settings = AgentSettings()
    assert settings.model_id == "configured-model"
    assert settings.aws_profile == "configure-project-profile"
    assert settings.aws_region == "sa-east-1"
    assert settings.max_requests == 3
    assert settings.max_tool_calls == 4
    assert settings.max_output_tokens == 512
    assert settings.request_timeout_seconds == 12.5
    assert AgentSettings(max_requests=2, aws_region="eu-west-1").max_requests == 2
    assert AgentSettings(aws_region="eu-west-1").aws_region == "eu-west-1"


def test_configuration_and_placeholder_profile_do_not_require_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_PROFILE", "configure-project-profile")
    monkeypatch.setenv("AWS_REGION", "sa-east-1")
    settings = load_agent_settings()
    assert settings.aws_profile == "configure-project-profile"
    assert settings.aws_region == "sa-east-1"
    with pytest.raises(ConfigurationError):
        create_agent(settings)


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("AGENT_MAX_REQUESTS", "0"),
        ("AGENT_MAX_REQUESTS", "21"),
        ("AGENT_MAX_TOOL_CALLS", "3.0"),
        ("AGENT_MAX_TOOL_CALLS", "true"),
        ("AGENT_MAX_OUTPUT_TOKENS", "4097"),
        ("AGENT_REQUEST_TIMEOUT_SECONDS", "nan"),
        ("AGENT_REQUEST_TIMEOUT_SECONDS", "121"),
        ("BEDROCK_MODEL_ID", " "),
        ("AWS_DEFAULT_REGION", " "),
    ],
)
def test_invalid_environment_settings_fail_with_sanitized_error(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    monkeypatch.setenv(variable, value)
    with pytest.raises(
        ConfigurationError, match="^Invalid agent environment configuration$"
    ) as error:
        load_agent_settings()
    assert isinstance(error.value.__cause__, ValidationError)


@pytest.mark.parametrize("value", [True, 3.0])
def test_explicit_request_budget_rejects_boolean_and_float(value: object) -> None:
    with pytest.raises(ValidationError):
        AgentSettings.model_validate({"max_requests": value})


def test_settings_leave_dotenv_loading_to_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("AGENT_MAX_REQUESTS=0\n")
    monkeypatch.chdir(tmp_path)
    assert load_agent_settings().max_requests == 5


def test_live_probe_requires_explicit_opt_in() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "emporio_music.agent.smoke"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 2 and "--live is required" in result.stderr
    assert not result.stdout
