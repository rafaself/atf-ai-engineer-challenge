"""The opt-in probe must retain failed-run evidence and refuse unbudgeted calls."""

import asyncio
import json
from pathlib import Path

import pytest
from emporio_music.agent.factory import create_agent
from emporio_music.agent.settings import AgentSettings
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import (
    ConversationMessage,
    ConversationSession,
    ExecutionContext,
)
from emporio_music.domain.errors import AgentExecutionError
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from scripts.evaluation_support import RecordingAgent, write_checkpoint
from scripts.validate_us18 import (
    _probe_status,
    _record_failure,
    _run_status,
    validate,
)


def test_failed_probe_retains_messages_and_safe_cause_without_a_final_answer() -> None:
    async def invalid(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(
            parts=[TextPart("<thinking>Unacceptable draft</thinking>")]
        )

    recorder = RecordingAgent(
        create_agent(AgentSettings(), model=FunctionModel(invalid))
    )
    with pytest.raises(AgentExecutionError):
        asyncio.run(
            recorder.run(ChatRequest(message="Olá"), context=ExecutionContext())
        )
    assert recorder.evidence["usage"]["requests"] == 2
    assert recorder.evidence["failure"]["causes"][:2] == [
        "AgentExecutionError",
        "UnexpectedModelBehavior",
    ]
    assert recorder.evidence["messages"]
    assert all("run_id" not in message for message in recorder.evidence["messages"])


def test_recorder_counts_only_current_responses_with_assistant_history() -> None:
    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart("Resposta atual")])

    recorder = RecordingAgent(
        create_agent(AgentSettings(), model=FunctionModel(respond))
    )
    context = ExecutionContext(
        session=ConversationSession(),
        history=(
            ConversationMessage(role="user", content="Pergunta anterior"),
            ConversationMessage(role="assistant", content="Resposta anterior"),
        ),
    )
    asyncio.run(recorder.run(ChatRequest(message="E agora?"), context=context))
    assert recorder.evidence["usage"]["requests"] == 1
    assert len(recorder.evidence["usage"]["responses"]) == 1
    assert (
        len([m for m in recorder.evidence["messages"] if m["kind"] == "response"]) == 2
    )


def test_live_probe_refuses_insufficient_budget_before_provider_setup(
    tmp_path: Path,
) -> None:
    output = tmp_path / "capture.json"
    with pytest.raises(ValueError, match="reservation"):
        asyncio.run(validate(output, max_cost_usd=0.01))
    assert not output.exists()


def test_probe_reports_http_errors_as_failed_cases_not_successful_completion() -> None:
    assert _run_status(200) == "completed"
    assert _run_status(503) == "failed"
    assert _probe_status([{"status": "completed"}]) == "completed"
    assert _probe_status([{"status": "failed"}]) == "completed_with_failures"


def test_access_denial_diagnostic_keeps_actions_without_raw_provider_message() -> None:
    class Denied(Exception):
        response = {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "Missing aws-marketplace:Subscribe; private identity and provider body",
            }
        }

    async def denied(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise Denied("private details")

    recorder = RecordingAgent(
        create_agent(AgentSettings(), model=FunctionModel(denied))
    )
    with pytest.raises(Denied):
        asyncio.run(
            recorder.run(ChatRequest(message="Olá"), context=ExecutionContext())
        )
    assert recorder.evidence["access_denial"] == {
        "category": "marketplace_subscription_permissions",
        "mentioned_actions": ["aws-marketplace:subscribe"],
    }
    assert "private" not in json.dumps(recorder.evidence)


def test_probe_checkpoint_preserves_partial_trace_on_cancellation(
    tmp_path: Path,
) -> None:
    output = tmp_path / "capture.json"
    run = {"case_id": "mixed-order-return", "status": "in_progress"}
    report = {"status": "running", "phase": "http_request", "runs": [run]}
    evidence = {
        "messages": [{"kind": "model-response", "text": "partial answer"}],
        "usage": {"requests": 1, "input_tokens": 123, "output_tokens": 8},
    }

    with output.open("x") as stream:
        write_checkpoint(stream, report)
        assert json.loads(output.read_text())["status"] == "running"
        status = _record_failure(
            report,
            run,
            evidence,
            asyncio.CancelledError("private cancellation detail"),
            12.5,
        )
        write_checkpoint(stream, report)

    saved = json.loads(output.read_text())
    assert status == "interrupted"
    assert saved["status"] == "interrupted"
    assert saved["failed_phase"] == "http_request"
    assert saved["runs"][0]["status"] == "interrupted"
    assert saved["runs"][0]["elapsed_seconds"] == 12.5
    assert saved["runs"][0]["messages"] == evidence["messages"]
    assert saved["runs"][0]["usage"] == evidence["usage"]
    assert saved["failure"]["causes"] == ["CancelledError"]
    assert "private cancellation detail" not in json.dumps(saved)
