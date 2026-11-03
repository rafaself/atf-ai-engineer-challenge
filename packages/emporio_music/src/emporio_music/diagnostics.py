"""Temporary opt-in terminal diagnostics; never configure third-party SDK logging."""

import json
import logging
import os
from contextvars import ContextVar
from typing import Any

request_id: ContextVar[str] = ContextVar("pipeline_request_id", default="-")
_logger = logging.getLogger("emporio.pipeline")
_logger.setLevel(logging.INFO)
_logger.propagate = False
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)

# Per-event allowlists prevent current/future callers from accidentally dumping
# request content, credentials, customer identities, tool rows, or session history.
_FAILURE_FIELDS = {"causes", "aws_error_code", "hint"}
_SAFE_FIELDS = {
    "http.request": set(),
    "http.response": {"status", "duration_ms"},
    "http.failure": _FAILURE_FIELDS | {"duration_ms"},
    "provider.initializing": {"model", "aws_region", "explicit_profile"},
    "provider.ready": {"configured_model", "aws_region", "injected_model"},
    "provider.failure": _FAILURE_FIELDS,
    "agent.started": {"model", "aws_region"},
    "agent.completed": {"requests", "input_tokens", "output_tokens"},
    "output.rejected": {"reason", "retry"},
    "output.accepted": {"truncated_totals"},
    "tool.called": {"tool", "limit"},
    "tool.result": {"total_matches", "returned"},
    "catalog.result": {"total_matches", "returned"},
    "catalog.failure": _FAILURE_FIELDS,
    "operations.result": {"total_matches", "returned"},
    "operations.failure": _FAILURE_FIELDS,
    "operations.import.completed": {"customers", "orders", "items"},
    "catalog.import.completed": {"categories", "products", "promotions"},
}


def trace(event: str, **fields: object) -> None:
    if os.environ.get("PIPELINE_LOGS", "0") != "1":
        return
    payload = json.dumps(
        {
            "event": event,
            "request_id": request_id.get(),
            **{
                key: value
                for key, value in fields.items()
                if key in _SAFE_FIELDS.get(event, set())
            },
        },
        ensure_ascii=False,
        default=str,
    )
    # Redact active AWS credential values even if pasted into a chat message.
    secrets = sorted(
        (
            os.environ.get(key, "")
            for key in (
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
            )
        ),
        key=len,
        reverse=True,
    )
    for value in secrets:
        if value:
            escaped = json.dumps(value, ensure_ascii=False)[1:-1]
            payload = payload.replace(escaped, "[REDACTED]")
    _logger.info(payload)


def failure(error: BaseException) -> dict[str, Any]:
    """Summarize causes without raw exception bodies, paths, credentials or SDK payloads."""
    causes: list[str] = []
    code: str | None = None
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        causes.append(type(current).__name__)
        response = getattr(current, "response", None)
        if isinstance(response, dict):
            detail = response.get("Error")
            candidate = detail.get("Code") if isinstance(detail, dict) else None
            if isinstance(candidate, str) and candidate.isalnum():
                code = candidate
        current = current.__cause__
    hint = None
    if "ProfileNotFound" in causes:
        hint = "Configure the selected AWS profile, or remove AWS_PROFILE for key authentication."
    elif "TokenRetrievalError" in causes:
        hint = "Check the configured AWS token provider and its authentication state."
    elif code in (
        "UnrecognizedClientException",
        "ExpiredTokenException",
        "InvalidSignatureException",
    ):
        hint = "Check active credentials and the matching session token for temporary credentials."
    elif code == "AccessDeniedException":
        hint = "Check model invocation permissions and access in the configured region."
    return {"causes": causes, "aws_error_code": code, "hint": hint}
