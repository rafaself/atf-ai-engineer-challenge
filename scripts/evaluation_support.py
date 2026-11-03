"""Shared trace and capture helpers for repository evaluation scripts."""

from __future__ import annotations

import json
import re
from typing import Any, TextIO

from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.diagnostics import failure
from emporio_music.domain.chat import AgentResponse, ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from pydantic_ai import capture_run_messages
from pydantic_ai.messages import ModelMessagesTypeAdapter, ModelResponse


def sanitized(value: Any) -> Any:
    """Drop transient SDK identifiers, retaining actual model/tool evidence."""
    if isinstance(value, dict):
        return {
            key: sanitized(item)
            for key, item in value.items()
            if key
            not in {"timestamp", "run_id", "conversation_id", "provider_response_id"}
        }
    if isinstance(value, list):
        return [sanitized(item) for item in value]
    return value


def _usage_value(usage: Any, details: dict[str, Any], name: str) -> int | None:
    raw = getattr(usage, name, None)
    if raw is None:
        raw = details.get(name)
    return int(raw) if isinstance(raw, (int, float)) else None


def write_checkpoint(stream: TextIO, report: dict[str, Any]) -> None:
    """Flush the latest safe report state so interruptions retain progress."""
    stream.seek(0)
    stream.truncate()
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
    stream.flush()


class RecordingAgent:
    """Capture current model responses, usage, and safe failure metadata."""

    def __init__(self, executor: PydanticAgentExecutor) -> None:
        self.executor = executor
        self.evidence: dict[str, Any] = {}

    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        self.evidence = {}
        with capture_run_messages() as messages:
            try:
                return await self.executor.run(request, context=context)
            except Exception as exc:
                # Cause types/code, never raw exception bodies or credentials.
                self.evidence["failure"] = failure(exc)
                current: BaseException | None = exc
                while current is not None:
                    response = getattr(current, "response", None)
                    detail = (
                        response.get("Error", {}) if isinstance(response, dict) else {}
                    )
                    if detail.get("Code") == "AccessDeniedException":
                        message = str(detail.get("Message", "")).lower()
                        category = (
                            "marketplace_subscription_permissions"
                            if "aws-marketplace" in message or "marketplace" in message
                            else "anthropic_use_case_registration"
                            if "use case" in message or "usecase" in message
                            else "organization_policy"
                            if "service control policy" in message
                            else "identity_policy"
                            if "identity-based policy" in message
                            else "unclassified_access_denial"
                        )
                        self.evidence["access_denial"] = {
                            "category": category,
                            "mentioned_actions": sorted(
                                set(
                                    re.findall(
                                        r"(?:bedrock|aws-marketplace):[a-z]+",
                                        message,
                                    )
                                )
                            ),
                        }
                        break
                    current = current.__cause__
                raise
            finally:
                # Reconstructed assistant history has no run_id. Preserve it in
                # the trace, but do not count it as new inference.
                responses = [
                    message
                    for message in messages
                    if isinstance(message, ModelResponse) and message.run_id is not None
                ]
                response_usage: list[dict[str, int | None]] = []
                for response in responses:
                    usage = response.usage
                    details = getattr(usage, "details", None)
                    details = details if isinstance(details, dict) else {}
                    response_usage.append(
                        {
                            "input_tokens": _usage_value(
                                usage, details, "input_tokens"
                            ),
                            "output_tokens": _usage_value(
                                usage, details, "output_tokens"
                            ),
                            "cache_read_tokens": _usage_value(
                                usage, details, "cache_read_tokens"
                            ),
                            "cache_write_tokens": _usage_value(
                                usage, details, "cache_write_tokens"
                            ),
                            "reasoning_tokens": _usage_value(
                                usage, details, "reasoning_tokens"
                            ),
                        }
                    )

                def total(name: str) -> int | None:
                    value_total = 0
                    found = False
                    for item in response_usage:
                        value = item[name]
                        if value is not None:
                            value_total += value
                            found = True
                    return value_total if found else None

                self.evidence["messages"] = sanitized(
                    ModelMessagesTypeAdapter.dump_python(messages, mode="json")
                )
                self.evidence["usage"] = {
                    "requests": len(responses),
                    "input_tokens": total("input_tokens"),
                    "output_tokens": total("output_tokens"),
                    "cache_read_tokens": total("cache_read_tokens"),
                    "cache_write_tokens": total("cache_write_tokens"),
                    "reasoning_tokens": total("reasoning_tokens"),
                    "responses": response_usage,
                }
