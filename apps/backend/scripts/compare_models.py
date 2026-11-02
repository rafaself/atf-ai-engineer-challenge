"""Run the explicitly approved, bounded issue #40 Bedrock comparison."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

import boto3  # type: ignore[import-untyped]
import httpx
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]
from dotenv import dotenv_values
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

from emporio_music_backend import paths
from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.policies import LocalPolicySearch
from emporio_music_backend.agent.settings import AgentSettings, load_agent_settings
from emporio_music_backend.api.app import create_app
from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.contracts.conversations import HistoryLimits
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from scripts.validate_us18 import RecordingAgent, _write_checkpoint, sanitized

PROJECT_ROOT = paths.PROJECT_ROOT
SCENARIOS_PATH = PROJECT_ROOT / "docs/examples/model-comparison/scenarios.json"
PRICING_PATH = PROJECT_ROOT / "docs/examples/model-comparison/pricing.json"
AWS_ENVIRONMENT_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_DEFAULT_REGION",
    "AWS_REGION",
    "AWS_PROFILE",
)
ENDPOINT_RUNTIME = "bedrock-runtime"
EXPECTED_INFERENCE_ENDPOINTS = {
    "qwen3_32b": ENDPOINT_RUNTIME,
    "nova_micro": ENDPOINT_RUNTIME,
    "nova_lite": ENDPOINT_RUNTIME,
}
EXPECTED_INFERENCE_APIS = {
    "qwen3_32b": "converse",
    "nova_micro": "converse",
    "nova_lite": "converse",
}
EXPECTED_INFERENCE_MODEL_IDS = {
    "qwen3_32b": "qwen.qwen3-32b-v1:0",
    "nova_micro": "amazon.nova-micro-v1:0",
    "nova_lite": "amazon.nova-lite-v1:0",
}
OUTPUT_CAP_USD = Decimal("1.00")
EXPECTED_SETTINGS = {
    "request_timeout_seconds": 15.0,
    "max_requests": 5,
    "max_tool_calls": 5,
    "max_output_tokens": 1024,
}
RUN_ORDER = ("qwen3_32b", "nova_micro", "nova_lite")
EXPECTED_MODEL_IDS = {
    "qwen3_32b": "qwen.qwen3-32b-v1:0",
    "nova_micro": "amazon.nova-micro-v1:0",
    "nova_lite": "amazon.nova-lite-v1:0",
}
EXPECTED_CONTEXT_WINDOWS = {
    "qwen3_32b": 32_000,
    "nova_micro": 128_000,
    "nova_lite": 300_000,
}
SOURCE_PATHS = (
    "data/SHA256SUMS",
    "data/products.csv",
    "data/categories.csv",
    "data/promotions.csv",
    "data/customers.csv",
    "data/orders.csv",
    "data/order_items.csv",
    "data/store_policies.pdf",
    "data/policies/corpus.json",
    "data/policies/freeze.json",
    "data/catalog.sqlite3",
    "data/operations.sqlite3",
    "apps/backend/pyproject.toml",
    "apps/backend/uv.lock",
    "docs/examples/model-comparison/scenarios.json",
    "docs/examples/model-comparison/pricing.json",
    "docs/examples/model-comparison/protocol.md",
    "docs/examples/model-comparison/scenarios-frozen-v1.json",
)


@dataclass(frozen=True)
class Candidate:
    key: str
    model_id: str
    inference_endpoint: str
    inference_model_id: str
    inference_api: str
    context_window_tokens: int
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    tool_use_status: str


class RequestCounter:
    """Count provider HTTP attempts, including SDK retries."""

    def __init__(self) -> None:
        self.count = 0

    def before_call(self, **_kwargs: object) -> None:
        self.count += 1


def load_project_aws_environment() -> None:
    """Load project AWS settings without printing their values."""
    values = dotenv_values(PROJECT_ROOT / ".env", verbose=False)
    for name in AWS_ENVIRONMENT_KEYS:
        value = values.get(name)
        if value is not None:
            os.environ.setdefault(name, value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_sha256(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in directory.rglob("*") if item.is_file()):
        relative = path.relative_to(directory).as_posix().encode()
        digest.update(relative)
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _code_freeze() -> dict[str, object]:
    source_roots = (
        PROJECT_ROOT / "apps/backend/src",
        PROJECT_ROOT / "apps/backend/scripts",
    )
    files = sorted(
        path
        for root in source_roots
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    file_hashes = {
        path.relative_to(PROJECT_ROOT).as_posix(): _sha256(path) for path in files
    }
    status = subprocess.run(
        ["git", "status", "--short"],
        check=True,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    ).stdout
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    serialized = json.dumps(file_hashes, sort_keys=True).encode()
    return {
        "commit": commit,
        "working_tree_dirty": bool(status.strip()),
        "source_files_sha256": hashlib.sha256(serialized).hexdigest(),
        "source_file_count": len(file_hashes),
    }


def freeze_inputs() -> dict[str, object]:
    hashes = {relative: _sha256(PROJECT_ROOT / relative) for relative in SOURCE_PATHS}
    index_directory = paths.DATA_DIRECTORY / "policy-indexes"
    return {
        "application": _code_freeze(),
        "source_files_sha256": hashes,
        "policy_index_sha256": _tree_sha256(index_directory),
        "scenario_sha256": _sha256(SCENARIOS_PATH),
    }


def load_scenarios(path: Path = SCENARIOS_PATH) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    scenarios = document.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 9:
        raise ValueError("The frozen issue #40 set must contain nine scenarios")
    if sum(len(item.get("turns", [])) for item in scenarios) != 16:
        raise ValueError("The frozen issue #40 set must contain sixteen turns")
    if len({item.get("id") for item in scenarios}) != 9:
        raise ValueError("Scenario IDs must be unique")
    return scenarios


def load_verified_candidates(
    path: Path = PRICING_PATH, *, today: date | None = None
) -> list[Candidate]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("region") != "us-east-1" or document.get("currency") != "USD":
        raise ValueError("Pricing must be verified for USD in us-east-1")
    if document.get("service_tier") != "standard":
        raise ValueError("Only standard on-demand prices are in scope")
    if document.get("verified") is not True:
        raise ValueError("Current Bedrock prices have not been verified")
    checked_at = date.fromisoformat(str(document.get("checked_at_utc", ""))[:10])
    if checked_at != (today or datetime.now(UTC).date()):
        raise ValueError("Refresh the pricing verification on the day of the run")
    entries = document.get("models")
    if not isinstance(entries, list):
        raise ValueError("Pricing manifest has no model list")
    by_key = {entry.get("key"): entry for entry in entries}
    if set(by_key) != set(RUN_ORDER):
        raise ValueError(
            "Pricing manifest must contain exactly the three Runtime issue #40 models"
        )

    candidates: list[Candidate] = []
    for key in RUN_ORDER:
        entry = by_key[key]
        model_id = str(entry["model_id"])
        if model_id != EXPECTED_MODEL_IDS[key]:
            raise ValueError(f"Model ID for {key} must remain the issue #40 candidate")
        context_window = int(entry["context_window_tokens"])
        if context_window != EXPECTED_CONTEXT_WINDOWS[key]:
            raise ValueError(f"Refresh the verified context ceiling for {key}")
        inference_endpoint = str(entry.get("inference_endpoint", ""))
        if inference_endpoint != EXPECTED_INFERENCE_ENDPOINTS[key]:
            raise ValueError(
                f"Inference endpoint for {key} differs from the verified route"
            )
        inference_model_id = str(entry.get("inference_model_id", ""))
        if inference_model_id != EXPECTED_INFERENCE_MODEL_IDS[key]:
            raise ValueError(
                f"Inference model ID for {key} differs from the verified route"
            )
        inference_api = str(entry.get("inference_api", ""))
        if inference_api != EXPECTED_INFERENCE_APIS[key]:
            raise ValueError(f"Inference API for {key} differs from the verified route")
        tool_use_status = str(entry.get("tool_use_status", ""))
        if entry.get("rate_status") != "verified":
            raise ValueError(f"Current price for {key} is not verified")
        if not entry.get("source_url"):
            raise ValueError(f"Current price source for {key} is missing")
        candidates.append(
            Candidate(
                key=key,
                model_id=model_id,
                inference_endpoint=inference_endpoint,
                inference_model_id=inference_model_id,
                inference_api=inference_api,
                context_window_tokens=context_window,
                input_usd_per_million=Decimal(str(entry["input_usd_per_million"])),
                output_usd_per_million=Decimal(str(entry["output_usd_per_million"])),
                tool_use_status=tool_use_status,
            )
        )
    if any(
        candidate.context_window_tokens <= 0
        or not candidate.input_usd_per_million.is_finite()
        or candidate.input_usd_per_million <= 0
        or not candidate.output_usd_per_million.is_finite()
        or candidate.output_usd_per_million <= 0
        for candidate in candidates
    ):
        raise ValueError("Context ceilings and verified rates must be positive")
    return candidates


def validate_endpoint_tool_manifest(
    path: Path = PRICING_PATH, *, today: date | None = None
) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    checked_at = date.fromisoformat(
        str(document.get("endpoint_tool_checked_at_utc", ""))[:10]
    )
    if checked_at != (today or datetime.now(UTC).date()):
        raise ValueError("Refresh endpoint tool compatibility on the day of the run")
    entries = document.get("models")
    if not isinstance(entries, list):
        raise ValueError("Endpoint compatibility manifest has no model list")
    by_key = {entry.get("key"): entry for entry in entries}
    if set(by_key) != set(RUN_ORDER):
        raise ValueError("Endpoint compatibility manifest must list all three models")
    for key in RUN_ORDER:
        entry = by_key[key]
        if (
            entry.get("inference_endpoint") != EXPECTED_INFERENCE_ENDPOINTS[key]
            or entry.get("inference_model_id") != EXPECTED_INFERENCE_MODEL_IDS[key]
            or entry.get("inference_api") != EXPECTED_INFERENCE_APIS[key]
            or entry.get("tool_use_status")
            not in {"verified", "unverified", "unsupported"}
            or not entry.get("model_card_url")
        ):
            raise ValueError(f"Endpoint tool-use compatibility for {key} is incomplete")


def turn_reservation_usd(
    candidate: Candidate,
    *,
    max_requests: int = int(EXPECTED_SETTINGS["max_requests"]),
    max_output_tokens: int = int(EXPECTED_SETTINGS["max_output_tokens"]),
) -> Decimal:
    """Reserve a full input context and output cap for every allowed model request."""
    input_cost = candidate.context_window_tokens * candidate.input_usd_per_million
    output_cost = int(max_output_tokens) * candidate.output_usd_per_million
    return (int(max_requests) * (input_cost + output_cost)) / Decimal(1_000_000)


def request_reservation_usd(candidate: Candidate, max_output_tokens: int) -> Decimal:
    return (
        candidate.context_window_tokens * candidate.input_usd_per_million
        + max_output_tokens * candidate.output_usd_per_million
    ) / Decimal(1_000_000)


def estimate_usage_cost(
    candidate: Candidate,
    evidence: dict[str, Any],
    *,
    observed_requests: int,
    max_output_tokens: int,
) -> tuple[Decimal, dict[str, object]]:
    """Estimate cost, reserving a full request for every unreported usage record."""
    usage = evidence.get("usage", {})
    responses = usage.get("responses", [])
    request_cost_reservation = request_reservation_usd(candidate, max_output_tokens)
    known_cost = Decimal(0)
    complete = 0
    known_input = 0
    known_output = 0
    for response in responses:
        input_tokens = response.get("input_tokens")
        output_tokens = response.get("output_tokens")
        if input_tokens is None or output_tokens is None:
            continue
        input_count = int(input_tokens)
        output_count = int(output_tokens)
        known_input += input_count
        known_output += output_count
        known_cost += (
            input_count * candidate.input_usd_per_million
            + output_count * candidate.output_usd_per_million
        ) / Decimal(1_000_000)
        complete += 1

    missing_usage_requests = max(0, observed_requests - complete)
    estimated_cost = known_cost + missing_usage_requests * request_cost_reservation
    return estimated_cost, {
        "requests_observed": observed_requests,
        "requests_with_usage": complete,
        "requests_with_missing_usage": missing_usage_requests,
        "input_tokens_reported": known_input if complete else None,
        "output_tokens_reported": known_output if complete else None,
        "estimated_usd": str(estimated_cost.quantize(Decimal("0.00000001"))),
    }


def _availability_result(response: dict[str, Any], model_id: str) -> dict[str, object]:
    agreement = response.get("agreementAvailability", {}).get("status", "UNKNOWN")
    authorization = response.get("authorizationStatus", "UNKNOWN")
    entitlement = response.get("entitlementAvailability", {}).get("status", "UNKNOWN")
    region = response.get("regionAvailability", {}).get("status", "UNKNOWN")
    available = (
        agreement == "AVAILABLE"
        and authorization == "AUTHORIZED"
        and entitlement == "AVAILABLE"
        and region == "AVAILABLE"
    )
    return {
        "model_id": model_id,
        "status": "available" if available else "unavailable_or_unconfirmed",
        "agreement": agreement,
        "authorization": authorization,
        "entitlement": entitlement,
        "region": region,
    }


def probe_model_access(
    candidates: list[Candidate], settings: AgentSettings
) -> dict[str, Any]:
    """Use Bedrock's control-plane availability API; this does not invoke models."""
    results: list[dict[str, object]] = []
    try:
        session = boto3.Session(
            profile_name=settings.aws_profile,
            region_name="us-east-1",
        )
        client = session.client("bedrock")
    except Exception as exc:
        return {
            "status": "blocked",
            "failure_type": type(exc).__name__,
            "paid_calls": 0,
            "models": results,
        }
    for candidate in candidates:
        try:
            response = client.get_foundation_model_availability(
                modelId=candidate.model_id
            )
        except Exception as exc:
            result: dict[str, object] = {
                "status": "blocked",
                "failure_type": type(exc).__name__,
                "paid_calls": 0,
                "models": results,
            }
            if isinstance(exc, ClientError):
                result["aws_operation"] = exc.operation_name
                result["aws_error_code"] = exc.response.get("Error", {}).get("Code")
            return result
        results.append(_availability_result(response, candidate.model_id))
    return {
        "status": "checked",
        "paid_calls": 0,
        "models": results,
    }


def _validate_agent_limits(settings: AgentSettings) -> None:
    actual = {
        "request_timeout_seconds": settings.request_timeout_seconds,
        "max_requests": settings.max_requests,
        "max_tool_calls": settings.max_tool_calls,
        "max_output_tokens": settings.max_output_tokens,
    }
    if actual != EXPECTED_SETTINGS:
        raise ValueError(
            "Live comparison requires the frozen app limits: "
            + json.dumps(EXPECTED_SETTINGS, sort_keys=True)
        )


def _model_executor(
    candidate: Candidate,
    settings: AgentSettings,
    counter: RequestCounter,
    policy_data_directory: Path,
) -> Any:
    if (
        candidate.inference_endpoint != ENDPOINT_RUNTIME
        or candidate.inference_api != "converse"
    ):
        raise ValueError("Issue #40 candidates must use Bedrock Runtime Converse")
    session = boto3.Session(
        profile_name=settings.aws_profile,
        region_name=settings.aws_region,
    )
    client = session.client(
        "bedrock-runtime",
        config=Config(
            connect_timeout=5,
            read_timeout=settings.request_timeout_seconds,
            retries={"mode": "standard", "total_max_attempts": 1},
        ),
    )
    client.meta.events.register(
        "before-call.bedrock-runtime.Converse", counter.before_call
    )
    model = BedrockConverseModel(
        candidate.inference_model_id,
        provider=BedrockProvider(bedrock_client=client),
    )
    return create_store_agent(
        settings,
        SQLiteProductRepository(paths.CATALOG_DATABASE_PATH),
        SQLiteOrderRepository(paths.OPERATIONS_DATABASE_PATH),
        model=model,
        policy_search=LocalPolicySearch(data_directory=policy_data_directory),
    )


def _copy_policy_inputs(target: Path) -> Path:
    """Copy the frozen policy inputs so Chroma can only touch a temporary index."""
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(paths.DATA_DIRECTORY / "policies", target / "policies")
    shutil.copy2(paths.DATA_DIRECTORY / "store_policies.pdf", target)
    shutil.copytree(paths.DATA_DIRECTORY / "policy-indexes", target / "policy-indexes")
    return target


def _check_local_retrieval_readiness() -> dict[str, object]:
    """Load the existing local index and cached E5 model without network access."""
    try:
        result = LocalPolicySearch(data_directory=paths.DATA_DIRECTORY).search(
            "horário de funcionamento da loja"
        )
        if result["status"] != "evidence_found" or not result["records"]:
            return {
                "status": "blocked",
                "failure_type": "NoPolicyEvidence",
                "remediation": "Verify the existing local policy corpus and index.",
            }
    except Exception as exc:
        cause = exc.__cause__
        return {
            "status": "blocked",
            "failure_type": type(exc).__name__,
            "cause_type": type(cause).__name__ if cause else None,
            "missing_module": getattr(cause, "name", None),
            "remediation": (
                "Install local policy retrieval dependencies and prepare the cached "
                "E5 model and policy index using the repository README."
            ),
        }
    return {
        "status": "ready",
        "embedding_model": "intfloat/multilingual-e5-base",
        "index_collection": "policy-e5",
        "evidence_records": len(result["records"]),
    }


def _runtime_chat_settings() -> tuple[float, HistoryLimits]:
    """Match the production app's timeout and conversation history settings."""
    return (
        float(os.environ.get("CHAT_TIMEOUT_SECONDS", "60")),
        HistoryLimits(
            max_turns=int(os.environ.get("HISTORY_MAX_TURNS", "6")),
            max_characters=int(os.environ.get("HISTORY_MAX_CHARACTERS", "24000")),
        ),
    )


def _tool_calls(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for message in evidence.get("messages", []):
        for part in message.get("parts", []):
            if part.get("part_kind") == "tool-call":
                calls.append(
                    {
                        "name": part.get("tool_name"),
                        "arguments": part.get("args"),
                    }
                )
    return calls


def _not_executed(scenario: dict[str, Any], reason: str) -> dict[str, object]:
    return {
        "scenario_id": scenario["id"],
        "status": "not_executed",
        "reason": reason,
        "turns": [
            {"turn_index": index, "status": "not_executed"}
            for index, _ in enumerate(scenario["turns"], start=1)
        ],
        "manual_review": "pending",
    }


def _turn_cost_and_usage(
    candidate: Candidate,
    evidence: dict[str, Any],
    observed_requests: int,
    max_output_tokens: int,
) -> tuple[Decimal, dict[str, object]]:
    cost, usage = estimate_usage_cost(
        candidate,
        evidence,
        observed_requests=observed_requests,
        max_output_tokens=max_output_tokens,
    )
    cache_read = evidence.get("usage", {}).get("cache_read_tokens")
    cache_write = evidence.get("usage", {}).get("cache_write_tokens")
    reasoning = evidence.get("usage", {}).get("reasoning_tokens")
    usage["cache_read_tokens"] = cache_read
    usage["cache_write_tokens"] = cache_write
    usage["reasoning_tokens"] = reasoning
    usage["cost_note"] = (
        "Observed input/output at full standard rates; missing usage reserved at full context."
    )
    return cost, usage


def _summary(model_runs: list[dict[str, Any]]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for model in model_runs:
        scenarios = model.get("scenarios", [])
        attempted = [item for item in scenarios if item.get("attempted_turns", 0) > 0]
        evaluated = [item for item in attempted if item.get("status") == "completed"]
        latencies = [
            float(turn["end_to_end_latency_seconds"])
            for item in scenarios
            for turn in item.get("turns", [])
            if "end_to_end_latency_seconds" in turn
        ]
        total_cost = sum(
            (Decimal(str(item.get("estimated_cost_usd", "0"))) for item in scenarios),
            Decimal(0),
        )
        successful = sum(item.get("manual_verdict") == "pass" for item in evaluated)
        reviews_complete = bool(evaluated) and all(
            item.get("manual_review") == "complete" for item in evaluated
        )
        attempted_turns = sum(int(item.get("attempted_turns", 0)) for item in scenarios)
        reviewed_conversations = sum(
            item.get("manual_review") == "complete" for item in evaluated
        )
        failure_categories: dict[str, int] = {}
        for item in attempted:
            failure = item.get("execution_failure")
            if isinstance(failure, dict) and isinstance(failure.get("category"), str):
                category = failure["category"]
                failure_categories[category] = failure_categories.get(category, 0) + 1
        summary.append(
            {
                "model": model.get("model_id"),
                "scenario_verdicts": {
                    verdict: sum(
                        item.get("manual_verdict") == verdict for item in evaluated
                    )
                    for verdict in ("pass", "partial", "fail")
                },
                "attempted_conversations": len(attempted),
                "evaluated_conversations": len(evaluated),
                "reviewed_conversations": reviewed_conversations,
                "execution_failed_conversations": sum(
                    item.get("status") == "failed" for item in attempted
                ),
                "execution_failure_categories": failure_categories,
                "attempted_http_turns": attempted_turns,
                "not_executed_turns": sum(
                    turn.get("status") == "not_executed"
                    for item in scenarios
                    for turn in item.get("turns", [])
                ),
                "end_to_end_latency_samples": len(latencies),
                "critical_errors": sum(
                    len(item.get("critical_errors", [])) for item in evaluated
                )
                if reviews_complete
                else "pending_manual_review"
                if evaluated
                else None,
                "missed_tools": sum(
                    len(item.get("missed_tools", [])) for item in evaluated
                )
                if reviews_complete
                else "pending_manual_review"
                if evaluated
                else None,
                "unsupported_claims": sum(
                    len(item.get("unsupported_claims", [])) for item in evaluated
                )
                if reviews_complete
                else "pending_manual_review"
                if evaluated
                else None,
                "http_errors": sum(
                    isinstance(turn.get("http_status"), int)
                    and turn["http_status"] >= 400
                    for item in scenarios
                    for turn in item.get("turns", [])
                ),
                "tool_calls": sum(
                    len(turn.get("tool_calls", []))
                    for item in scenarios
                    for turn in item.get("turns", [])
                ),
                "requests_with_missing_usage": sum(
                    int(turn.get("usage", {}).get("requests_with_missing_usage", 0))
                    for item in scenarios
                    for turn in item.get("turns", [])
                ),
                "request_count_unknown_turns": model.get(
                    "request_count_unknown_turns", 0
                ),
                "model_calls": model.get("model_calls", 0),
                "input_tokens": model.get("input_tokens"),
                "output_tokens": model.get("output_tokens"),
                "total_estimated_usd": str(total_cost.quantize(Decimal("0.00000001"))),
                "cost_per_attempted_conversation_usd": str(
                    (total_cost / len(attempted)).quantize(Decimal("0.00000001"))
                )
                if attempted
                else None,
                "cost_per_fully_successful_conversation_usd": str(
                    (total_cost / successful).quantize(Decimal("0.00000001"))
                )
                if successful
                else None,
                "median_end_to_end_latency_seconds": round(
                    statistics.median(latencies), 3
                )
                if latencies
                else None,
                "maximum_end_to_end_latency_seconds": round(max(latencies), 3)
                if latencies
                else None,
            }
        )
    return summary


def _provider_unavailable(status_code: int | None, evidence: dict[str, Any]) -> bool:
    if status_code != 503:
        return False
    failure = evidence.get("failure")
    if not isinstance(failure, dict):
        return False
    causes = failure.get("causes", [])
    return "ProviderUnavailableError" in causes or bool(failure.get("aws_error_code"))


def _execution_failure_category(
    status_code: int | None,
    evidence: dict[str, Any],
    transport_failure_type: str | None,
) -> str:
    if transport_failure_type is not None:
        return "transport"
    failure = evidence.get("failure")
    if not isinstance(failure, dict):
        return "local_execution"
    causes = failure.get("causes", [])
    if failure.get("aws_error_code") or "ProviderUnavailableError" in causes:
        return "provider_or_sdk"
    if "PolicyRetrievalError" in causes or "ModuleNotFoundError" in causes:
        return "local_infrastructure"
    if status_code is None:
        return "transport"
    return "local_execution"


def _scenario_was_attempted(case: dict[str, Any]) -> bool:
    if int(case.get("attempted_turns", 0)) > 0:
        return True
    return any(
        turn.get("status") in {"completed", "failed"}
        for turn in case.get("turns", [])
        if isinstance(turn, dict)
    )


def _load_resume_capture(
    path: Path,
    *,
    candidates: list[Candidate],
    scenarios: list[dict[str, Any]],
    current_freeze: dict[str, Any],
) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Resume capture is not readable JSON") from exc
    if not isinstance(report, dict):
        raise ValueError("Resume capture must contain an object")
    if report.get("issue") != 40 or report.get("region") != "us-east-1":
        raise ValueError("Resume capture is not an issue #40 us-east-1 run")
    if report.get("status") != "stopped_provider_failure":
        raise ValueError("Only a provider-stopped issue #40 capture can be resumed")

    previous_freeze = report.get("source_freeze")
    if not isinstance(previous_freeze, dict):
        raise ValueError("Resume capture has no source freeze")
    for key in ("source_files_sha256", "policy_index_sha256", "scenario_sha256"):
        if previous_freeze.get(key) != current_freeze.get(key):
            raise ValueError(f"Resume capture {key} differs from the current run")
    previous_application = previous_freeze.get("application")
    current_application = current_freeze.get("application")
    if (
        not isinstance(previous_application, dict)
        or not isinstance(current_application, dict)
        or previous_application.get("commit") != current_application.get("commit")
    ):
        raise ValueError(
            "Resume capture application commit differs from the current run"
        )

    model_runs = report.get("model_runs")
    expected_by_id = {candidate.model_id: candidate for candidate in candidates}
    if not isinstance(model_runs, list):
        raise ValueError("Resume capture has no model runs")
    by_id = {
        item.get("model_id"): item for item in model_runs if isinstance(item, dict)
    }
    if set(by_id) != set(expected_by_id):
        raise ValueError("Resume capture model set differs from the current matrix")

    qwen = by_id.get(EXPECTED_MODEL_IDS["qwen3_32b"])
    if not isinstance(qwen, dict) or int(qwen.get("model_calls", 0)) <= 0:
        raise ValueError("Resume capture does not contain a successful Qwen baseline")
    expected_scenario_ids = {str(item["id"]) for item in scenarios}
    for model_id, candidate in expected_by_id.items():
        model = by_id[model_id]
        if not isinstance(model, dict):
            raise ValueError("Resume capture contains an invalid model entry")
        if (
            model.get("inference_endpoint", candidate.inference_endpoint)
            != candidate.inference_endpoint
            or model.get("inference_model_id", candidate.inference_model_id)
            != candidate.inference_model_id
            or model.get("inference_api", candidate.inference_api)
            != candidate.inference_api
        ):
            raise ValueError("Resume capture endpoint routes differ from the matrix")
        model_scenarios = model.get("scenarios")
        if not isinstance(model_scenarios, list):
            raise ValueError("Resume capture has no scenario outcomes")
        if {
            str(case.get("scenario_id"))
            for case in model_scenarios
            if isinstance(case, dict)
        } != expected_scenario_ids:
            raise ValueError("Resume capture scenario set differs from the matrix")
        for case in model_scenarios:
            if not isinstance(case, dict):
                continue
            for turn in case.get("turns", []):
                if not isinstance(turn, dict):
                    continue
                evidence = turn.get("model_trace")
                if isinstance(evidence, dict) and _provider_unavailable(
                    turn.get("http_status"), evidence
                ):
                    raise ValueError(
                        "Resume capture contains an unresolved provider failure"
                    )
    for captured_id, model in by_id.items():
        if (
            captured_id != EXPECTED_MODEL_IDS["qwen3_32b"]
            and int(model.get("model_calls", 0)) > 0
        ):
            raise ValueError(
                "Resume capture already contains paid calls for a later model"
            )

    try:
        previous_spend = Decimal(str(report.get("estimated_spend_usd", "0")))
    except Exception as exc:
        raise ValueError("Resume capture has invalid estimated spend") from exc
    if (
        not previous_spend.is_finite()
        or previous_spend < 0
        or previous_spend > OUTPUT_CAP_USD
    ):
        raise ValueError("Resume capture spend is outside the approved cap")
    report["model_runs"] = [by_id[candidate.model_id] for candidate in candidates]
    return report


async def run_comparison(
    *,
    output: Path,
    max_cost_usd: Decimal,
    pricing_path: Path = PRICING_PATH,
    resume_from: Path | None = None,
) -> dict[str, Any]:
    if (
        not max_cost_usd.is_finite()
        or max_cost_usd <= 0
        or max_cost_usd > OUTPUT_CAP_USD
    ):
        raise ValueError("The approved issue #40 spend cap is US$1.00")
    scenarios = load_scenarios()
    settings = load_agent_settings()
    _validate_agent_limits(settings)
    chat_timeout, history_limits = _runtime_chat_settings()
    current_freeze = freeze_inputs()

    with output.open("x", encoding="utf-8") as stream:
        report: dict[str, Any] = {
            "issue": 40,
            "status": "running",
            "phase": "preflight",
            "region": "us-east-1",
            "approved_max_cost_usd": str(max_cost_usd),
            "pricing_file": pricing_path.relative_to(PROJECT_ROOT).as_posix(),
            "paid_calls": 0,
            "provider_request_count_unknown_turns": 0,
            "source_freeze": current_freeze,
            "runtime_settings_verified": True,
            "scenario_count": len(scenarios),
            "planned_turns_per_model": 16,
            "model_runs": [],
        }
        _write_checkpoint(stream, report)

        try:
            candidates = load_verified_candidates(pricing_path)
            report["pricing_verification"] = "verified_today"
            _write_checkpoint(stream, report)
        except (ValueError, KeyError, TypeError) as exc:
            report["pricing_verification"] = "pending"
            report["pricing_failure_type"] = type(exc).__name__
            report["status"] = "blocked_pricing_verification"
            report["phase"] = "preflight_blocked"
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            _write_checkpoint(stream, report)
            return report

        try:
            validate_endpoint_tool_manifest(pricing_path)
            report["endpoint_tool_manifest_freshness"] = "current"
        except (ValueError, KeyError, TypeError) as exc:
            report["endpoint_tool_manifest_freshness"] = "stale_or_incomplete"
            report["endpoint_tool_failure_type"] = type(exc).__name__
            report["status"] = "blocked_endpoint_tool_verification"
            report["phase"] = "preflight_blocked"
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            _write_checkpoint(stream, report)
            return report

        report["endpoint_tool_compatibility"] = {
            candidate.inference_model_id: {
                "endpoint": candidate.inference_endpoint,
                "api": candidate.inference_api,
                "status": candidate.tool_use_status,
            }
            for candidate in candidates
        }
        _write_checkpoint(stream, report)
        if resume_from is not None:
            report = _load_resume_capture(
                resume_from,
                candidates=candidates,
                scenarios=scenarios,
                current_freeze=current_freeze,
            )
            report["resume_from_capture"] = str(resume_from)
            report["resume_source_freeze"] = current_freeze
            report.pop("summary", None)
            report.pop("finished_at_utc", None)
            report["approved_max_cost_usd"] = str(max_cost_usd)
            report["status"] = "running"
            report["phase"] = "preflight"
            report["resumed_at_utc"] = datetime.now(UTC).isoformat()
            report["pricing_verification"] = "verified_today"
            report["endpoint_tool_manifest_freshness"] = "current"
            report["endpoint_tool_compatibility"] = {
                candidate.inference_model_id: {
                    "endpoint": candidate.inference_endpoint,
                    "api": candidate.inference_api,
                    "status": candidate.tool_use_status,
                }
                for candidate in candidates
            }
            report["estimated_spend_usd"] = str(
                Decimal(str(report.get("estimated_spend_usd", "0")))
            )
            _write_checkpoint(stream, report)
        report["retrieval_readiness"] = _check_local_retrieval_readiness()
        _write_checkpoint(stream, report)
        if report["retrieval_readiness"]["status"] != "ready":
            report["status"] = "blocked_retrieval_readiness"
            report["phase"] = "preflight_blocked"
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            _write_checkpoint(stream, report)
            return report
        try:
            if resume_from is not None:
                access = report.get("account_preflight")
                if not isinstance(access, dict):
                    raise ValueError("Resume capture has no account preflight")
            else:
                access = probe_model_access(candidates, settings)
            report["account_preflight"] = access
            _write_checkpoint(stream, report)
            availability: dict[str, str] | None = None
            if access["status"] == "checked":
                availability = {
                    str(item["model_id"]): str(item["status"])
                    for item in access["models"]
                }
            elif access.get("failure_type") == "AccessDeniedException":
                report["account_preflight_resolution"] = (
                    "availability_api_denied_use_approved_baseline_probe"
                )
                _write_checkpoint(stream, report)
            else:
                report["status"] = "blocked_preflight"
                report["phase"] = "preflight_blocked"
                report["finished_at_utc"] = datetime.now(UTC).isoformat()
                _write_checkpoint(stream, report)
                return report

            baseline = next(
                candidate for candidate in candidates if candidate.key == "qwen3_32b"
            )
            baseline_id = next(
                candidate.model_id
                for candidate in candidates
                if candidate.key == "qwen3_32b"
            )
            if (
                availability is not None
                and availability.get(baseline_id) != "available"
            ):
                report["status"] = "blocked_baseline_unavailable"
                report["phase"] = "preflight_blocked"
                report["finished_at_utc"] = datetime.now(UTC).isoformat()
                _write_checkpoint(stream, report)
                return report
            if baseline.tool_use_status != "verified":
                report["status"] = "blocked_baseline_tool_compatibility"
                report["phase"] = "preflight_blocked"
                report["finished_at_utc"] = datetime.now(UTC).isoformat()
                _write_checkpoint(stream, report)
                return report
            price_by_key = {candidate.key: candidate for candidate in candidates}
            aggregate_cost = Decimal(str(report.get("estimated_spend_usd", "0")))
            stop_all = False
            stop_reason: str | None = None

            existing_models = {
                item.get("model_id"): item
                for item in report["model_runs"]
                if isinstance(item, dict)
            }
            for model_key in RUN_ORDER:
                candidate = price_by_key[model_key]
                candidate_fields: dict[str, Any] = {
                    "model_id": candidate.model_id,
                    "inference_endpoint": candidate.inference_endpoint,
                    "inference_model_id": candidate.inference_model_id,
                    "inference_api": candidate.inference_api,
                    "context_window_tokens": candidate.context_window_tokens,
                    "input_usd_per_million": str(candidate.input_usd_per_million),
                    "output_usd_per_million": str(candidate.output_usd_per_million),
                }
                model_report = existing_models.get(candidate.model_id)
                if model_report is None:
                    model_report = candidate_fields.copy()
                    report["model_runs"].append(model_report)
                    existing_models[candidate.model_id] = model_report
                else:
                    model_report.update(candidate_fields)
                model_report["status"] = "running"
                for name, default in (
                    ("scenarios", []),
                    ("model_calls", 0),
                    ("request_count_unknown_turns", 0),
                    ("input_tokens", None),
                    ("output_tokens", None),
                    ("requests_with_missing_usage", 0),
                    ("estimated_cost_usd", "0"),
                    ("sdk_max_attempts_per_request", 1),
                ):
                    model_report.setdefault(name, default)
                if stop_all:
                    model_report["status"] = (
                        "not_executed_budget_cap"
                        if stop_reason == "approved_cost_cap"
                        else "not_executed_provider_failure"
                    )
                    if not model_report["scenarios"]:
                        model_report["scenarios"] = [
                            _not_executed(item, stop_reason or "run_stopped")
                            for item in scenarios
                        ]
                    _write_checkpoint(stream, report)
                    continue
                if (
                    availability is not None
                    and availability.get(candidate.model_id) != "available"
                ):
                    model_report["status"] = "excluded_unavailable"
                    model_report["scenarios"] = [
                        _not_executed(item, "model_unavailable_or_unconfirmed")
                        for item in scenarios
                    ]
                    _write_checkpoint(stream, report)
                    continue
                if candidate.tool_use_status != "verified":
                    model_report["status"] = (
                        "excluded_endpoint_tool_compatibility_unverified"
                    )
                    model_report["scenarios"] = [
                        _not_executed(item, "endpoint_tool_compatibility_unverified")
                        for item in scenarios
                    ]
                    _write_checkpoint(stream, report)
                    continue
                counter = RequestCounter()
                model_settings = AgentSettings(
                    model_id=candidate.inference_model_id,
                    aws_region="us-east-1",
                    aws_profile=settings.aws_profile,
                    request_timeout_seconds=settings.request_timeout_seconds,
                    max_requests=settings.max_requests,
                    max_tool_calls=settings.max_tool_calls,
                    max_output_tokens=settings.max_output_tokens,
                )
                temporary = tempfile.TemporaryDirectory(prefix="issue40-")
                try:
                    policy_data_directory = _copy_policy_inputs(
                        Path(temporary.name) / "policy-data"
                    )
                    executor = _model_executor(
                        candidate,
                        model_settings,
                        counter,
                        policy_data_directory,
                    )
                except Exception as exc:
                    temporary.cleanup()
                    model_report["status"] = "excluded_provider_setup_failure"
                    model_report["failure_type"] = type(exc).__name__
                    model_report["scenarios"] = [
                        _not_executed(item, "provider_setup_failure")
                        for item in scenarios
                    ]
                    if model_key == "qwen3_32b":
                        stop_all = True
                        stop_reason = "baseline_provider_setup_failure"
                        report["status"] = "stopped_provider_failure"
                        report["phase"] = "preflight"
                    _write_checkpoint(stream, report)
                    continue

                with temporary as temporary_path:
                    recorder = RecordingAgent(executor)
                    service = ChatService(
                        recorder,
                        SQLiteConversationRepository(
                            Path(temporary_path) / "conversations.sqlite3"
                        ),
                        timeout_seconds=chat_timeout,
                        history_limits=history_limits,
                    )
                    app = create_app(service)
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(
                            app=app, raise_app_exceptions=False
                        ),
                        base_url="http://issue40.local",
                    ) as client:
                        stop_model = False
                        existing_scenarios = {
                            case.get("scenario_id"): index
                            for index, case in enumerate(model_report["scenarios"])
                            if isinstance(case, dict)
                        }
                        for scenario in scenarios:
                            scenario_id = str(scenario["id"])
                            existing_index = existing_scenarios.get(scenario_id)
                            if existing_index is not None and _scenario_was_attempted(
                                model_report["scenarios"][existing_index]
                            ):
                                continue
                            case: dict[str, Any] = {
                                "scenario_id": scenario_id,
                                "status": "running",
                                "manual_review": "pending",
                                "manual_verdict": None,
                                "expected": scenario.get("expected", {}),
                                "critical_errors": [],
                                "missed_tools": [],
                                "unsupported_claims": [],
                                "review_notes": None,
                                "attempted_turns": 0,
                                "estimated_cost_usd": "0",
                                "turns": [],
                            }
                            if existing_index is None:
                                model_report["scenarios"].append(case)
                                existing_scenarios[scenario_id] = (
                                    len(model_report["scenarios"]) - 1
                                )
                            else:
                                model_report["scenarios"][existing_index] = case
                            session_id: str | None = None
                            scenario_failed = False
                            for index, prompt in enumerate(scenario["turns"], start=1):
                                reservation = turn_reservation_usd(
                                    candidate,
                                    max_requests=settings.max_requests,
                                    max_output_tokens=settings.max_output_tokens,
                                )
                                if aggregate_cost + reservation > max_cost_usd:
                                    case["status"] = "not_executed_budget_cap"
                                    case["reason"] = (
                                        "full_turn_reservation_exceeds_remaining_cap"
                                    )
                                    case["turns"].extend(
                                        {
                                            "turn_index": remaining,
                                            "status": "not_executed",
                                        }
                                        for remaining in range(
                                            index, len(scenario["turns"]) + 1
                                        )
                                    )
                                    model_report["status"] = "stopped_at_budget_cap"
                                    stop_all = True
                                    report["status"] = "stopped_at_budget_cap"
                                    report["phase"] = "evaluation"
                                    break

                                if hasattr(recorder, "evidence"):
                                    recorder.evidence = {}
                                count_before = counter.count
                                request_started = perf_counter()
                                payload: dict[str, Any] = {"message": prompt["message"]}
                                if session_id is not None:
                                    payload["session_id"] = session_id
                                if "customer_id" in scenario:
                                    payload["customer_id"] = scenario["customer_id"]
                                response: httpx.Response | None = None
                                body: dict[str, Any]
                                transport_failure_type: str | None = None
                                try:
                                    response = await client.post(
                                        "/api/chat", json=payload
                                    )
                                    elapsed = round(perf_counter() - request_started, 3)
                                    try:
                                        parsed_body = response.json()
                                    except ValueError:
                                        body = {"detail": "HTTP response was not JSON"}
                                    else:
                                        body = (
                                            parsed_body
                                            if isinstance(parsed_body, dict)
                                            else {
                                                "detail": "HTTP response JSON was not an object"
                                            }
                                        )
                                except Exception as exc:
                                    elapsed = round(perf_counter() - request_started, 3)
                                    response = None
                                    body = {"detail": "HTTP evaluation request failed"}
                                    transport_failure_type = type(exc).__name__

                                if (
                                    response is not None
                                    and 200 <= response.status_code < 300
                                ):
                                    returned_session_id = body.pop("session_id", None)
                                    if isinstance(returned_session_id, str):
                                        session_id = returned_session_id
                                        turn_status = "completed"
                                    else:
                                        turn_status = "failed"
                                else:
                                    turn_status = "failed"
                                    if isinstance(body, dict):
                                        body.pop("session_id", None)

                                evidence = sanitized(recorder.evidence)
                                observed_api_requests = counter.count - count_before
                                reported_responses = evidence.get("usage", {}).get(
                                    "requests", 0
                                )
                                response_count = (
                                    int(reported_responses)
                                    if isinstance(reported_responses, int)
                                    else 0
                                )
                                api_requests = max(
                                    observed_api_requests, response_count
                                )
                                turn_cost, usage_summary = _turn_cost_and_usage(
                                    candidate,
                                    evidence,
                                    api_requests,
                                    settings.max_output_tokens,
                                )
                                counter_unavailable = (
                                    response is None and observed_api_requests == 0
                                )
                                if counter_unavailable:
                                    turn_cost = reservation
                                    report["provider_request_count_unknown_turns"] += 1
                                    model_report["request_count_unknown_turns"] += 1
                                    usage_summary["requests_with_missing_usage"] = (
                                        settings.max_requests
                                    )
                                    usage_summary["cost_note"] = (
                                        "No provider request count was available; the full HTTP-turn "
                                        "reservation is held against the cap."
                                    )
                                aggregate_cost += turn_cost
                                report["paid_calls"] += api_requests
                                report["estimated_spend_usd"] = str(aggregate_cost)
                                case["estimated_cost_usd"] = str(
                                    Decimal(case["estimated_cost_usd"]) + turn_cost
                                )
                                case["attempted_turns"] += 1
                                model_report["model_calls"] += api_requests
                                missing_usage = usage_summary[
                                    "requests_with_missing_usage"
                                ]
                                if isinstance(missing_usage, int):
                                    model_report["requests_with_missing_usage"] += (
                                        missing_usage
                                    )
                                input_tokens_reported = usage_summary[
                                    "input_tokens_reported"
                                ]
                                if isinstance(input_tokens_reported, int):
                                    model_report["input_tokens"] = (
                                        int(model_report["input_tokens"] or 0)
                                        + input_tokens_reported
                                    )
                                output_tokens_reported = usage_summary[
                                    "output_tokens_reported"
                                ]
                                if isinstance(output_tokens_reported, int):
                                    model_report["output_tokens"] = (
                                        int(model_report["output_tokens"] or 0)
                                        + output_tokens_reported
                                    )
                                turn_record: dict[str, Any] = {
                                    "turn_index": index,
                                    "prompt": prompt["message"],
                                    "status": turn_status,
                                    "http_status": response.status_code
                                    if response is not None
                                    else None,
                                    "end_to_end_latency_seconds": elapsed,
                                    "model_api_requests": api_requests,
                                    "provider_request_counter": observed_api_requests,
                                    "model_response_count": response_count,
                                    "reservation_upper_usd": str(
                                        reservation.quantize(Decimal("0.00000001"))
                                    ),
                                    "usage": usage_summary,
                                    "tool_calls": _tool_calls(evidence),
                                    "http_response": body,
                                    "model_trace": evidence,
                                }
                                if counter_unavailable:
                                    turn_record["request_count_unavailable"] = True
                                if transport_failure_type is not None:
                                    turn_record["transport_failure_type"] = (
                                        transport_failure_type
                                    )
                                case["turns"].append(turn_record)
                                _write_checkpoint(stream, report)

                                if turn_status == "failed":
                                    scenario_failed = True
                                    case["execution_failure"] = {
                                        "category": _execution_failure_category(
                                            response.status_code
                                            if response is not None
                                            else None,
                                            evidence,
                                            transport_failure_type,
                                        ),
                                        "http_status": response.status_code
                                        if response is not None
                                        else None,
                                    }
                                    case["turns"].extend(
                                        {
                                            "turn_index": remaining,
                                            "status": "not_executed",
                                        }
                                        for remaining in range(
                                            index + 1, len(scenario["turns"]) + 1
                                        )
                                    )
                                    if response is not None and _provider_unavailable(
                                        response.status_code, evidence
                                    ):
                                        stop_model = True
                                    break

                            if case["status"] == "not_executed_budget_cap":
                                break
                            case["status"] = (
                                "failed" if scenario_failed else "completed"
                            )
                            if stop_model:
                                case["reason"] = "provider_unavailable"
                                for remaining_scenario in scenarios[
                                    len(model_report["scenarios"]) :
                                ]:
                                    model_report["scenarios"].append(
                                        _not_executed(
                                            remaining_scenario, "provider_unavailable"
                                        )
                                    )
                                model_report["status"] = "stopped_provider_failure"
                                stop_all = True
                                stop_reason = "provider_unavailable"
                                report["status"] = "stopped_provider_failure"
                                report["phase"] = "evaluation"
                                break
                            _write_checkpoint(stream, report)

                model_total = sum(
                    (
                        Decimal(str(item.get("estimated_cost_usd", "0")))
                        for item in model_report["scenarios"]
                    ),
                    Decimal(0),
                )
                model_report["estimated_cost_usd"] = str(model_total)
                if model_report["status"] == "running":
                    model_report["status"] = (
                        "completed_with_failures"
                        if any(
                            item.get("status") == "failed"
                            for item in model_report["scenarios"]
                        )
                        else "completed"
                    )
                report["estimated_spend_usd"] = str(aggregate_cost)
                if stop_all:
                    for remaining_model in RUN_ORDER[RUN_ORDER.index(model_key) + 1 :]:
                        pending = price_by_key[remaining_model]
                        pending_report = existing_models.get(pending.model_id)
                        if pending_report is None:
                            pending_report = {
                                "model_id": pending.model_id,
                                "status": "not_executed_budget_cap"
                                if stop_reason == "approved_cost_cap"
                                else "not_executed_provider_failure",
                                "model_calls": 0,
                                "scenarios": [
                                    _not_executed(item, stop_reason or "run_stopped")
                                    for item in scenarios
                                ],
                            }
                            report["model_runs"].append(pending_report)
                            existing_models[pending.model_id] = pending_report
                        else:
                            pending_report["status"] = (
                                "not_executed_budget_cap"
                                if stop_reason == "approved_cost_cap"
                                else "not_executed_provider_failure"
                            )
                    break
                if stop_model:
                    continue
                _write_checkpoint(stream, report)

            report["summary"] = _summary(report["model_runs"])
            report["status"] = report.get("status", "completed")
            if report["status"] == "running":
                report["status"] = "completed"
            if report["status"] != "stopped_provider_failure":
                report["phase"] = "completed"
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            _write_checkpoint(stream, report)
            return report
        except BaseException as exc:
            report["status"] = (
                "interrupted"
                if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError))
                else "failed"
            )
            report["phase"] = report.get("phase", "preflight")
            report["failure_type"] = type(exc).__name__
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            _write_checkpoint(stream, report)
            raise


def preflight_report(
    *, output: Path, pricing_path: Path = PRICING_PATH
) -> dict[str, Any]:
    scenarios = load_scenarios()
    settings = load_agent_settings()
    _validate_agent_limits(settings)
    chat_timeout, history_limits = _runtime_chat_settings()
    with output.open("x", encoding="utf-8") as stream:
        report: dict[str, Any] = {
            "issue": 40,
            "status": "preflight_running",
            "region": "us-east-1",
            "paid_calls": 0,
            "approved_cost_cap_usd": str(OUTPUT_CAP_USD),
            "scenario_count": len(scenarios),
            "planned_turns_per_model": 16,
            "pricing_file": pricing_path.relative_to(PROJECT_ROOT).as_posix(),
            "source_freeze": freeze_inputs(),
            "runtime_settings_verified": True,
        }
        _write_checkpoint(stream, report)
        try:
            try:
                candidates = load_verified_candidates(pricing_path)
                report["pricing_verification"] = "verified_today"
            except (ValueError, KeyError, TypeError) as exc:
                candidates = []
                report["pricing_verification"] = "pending"
                report["pricing_failure_type"] = type(exc).__name__
            # Use the three known Runtime IDs for access probing while rates refresh.
            if not candidates:
                document = json.loads(pricing_path.read_text(encoding="utf-8"))
                entries = document.get("models")
                if not isinstance(entries, list):
                    raise ValueError("Pricing manifest has no model list")
                by_key = {entry.get("key"): entry for entry in entries}
                if set(by_key) != set(RUN_ORDER):
                    raise ValueError(
                        "Preflight requires the exact three Runtime issue #40 candidates"
                    )
                candidates = [
                    Candidate(
                        key=key,
                        model_id=EXPECTED_MODEL_IDS[key],
                        inference_endpoint=str(
                            entry.get("inference_endpoint", "unverified")
                        ),
                        inference_model_id=str(
                            entry.get("inference_model_id", "unverified")
                        ),
                        inference_api=str(entry.get("inference_api", "unverified")),
                        context_window_tokens=EXPECTED_CONTEXT_WINDOWS[key],
                        input_usd_per_million=Decimal(
                            str(entry["input_usd_per_million"])
                        ),
                        output_usd_per_million=Decimal(
                            str(entry["output_usd_per_million"])
                        ),
                        tool_use_status=str(entry.get("tool_use_status", "unverified")),
                    )
                    for key in RUN_ORDER
                    for entry in [by_key[key]]
                ]
            try:
                validate_endpoint_tool_manifest(pricing_path)
                report["endpoint_tool_manifest_freshness"] = "current"
            except (ValueError, KeyError, TypeError) as exc:
                report["endpoint_tool_manifest_freshness"] = "stale_or_incomplete"
                report["endpoint_tool_failure_type"] = type(exc).__name__
            report["retrieval_readiness"] = _check_local_retrieval_readiness()
            _write_checkpoint(stream, report)
            if report["retrieval_readiness"]["status"] != "ready":
                report["status"] = "blocked_retrieval_readiness"
                report["phase"] = "preflight_blocked"
                report["finished_at_utc"] = datetime.now(UTC).isoformat()
                _write_checkpoint(stream, report)
                return report
            report["account_preflight"] = probe_model_access(candidates, settings)
            report["endpoint_tool_compatibility"] = {
                candidate.inference_model_id: {
                    "endpoint": candidate.inference_endpoint,
                    "api": candidate.inference_api,
                    "status": candidate.tool_use_status,
                }
                for candidate in candidates
            }
            if report["account_preflight"]["status"] != "checked":
                report["status"] = "blocked_preflight"
            elif {
                str(item["model_id"]): item["status"]
                for item in report["account_preflight"]["models"]
            }.get("qwen.qwen3-32b-v1:0") != "available":
                report["status"] = "blocked_baseline_unavailable"
            elif report["endpoint_tool_manifest_freshness"] != "current":
                report["status"] = "blocked_endpoint_tool_verification"
            elif any(
                candidate.model_id == "qwen.qwen3-32b-v1:0"
                and candidate.tool_use_status != "verified"
                for candidate in candidates
            ):
                report["status"] = "blocked_baseline_tool_compatibility"
            elif report["pricing_verification"] != "verified_today":
                report["status"] = "blocked_pricing_verification"
            else:
                report["status"] = "ready_no_paid_calls"
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            _write_checkpoint(stream, report)
            return report
        except BaseException as exc:
            report["status"] = "blocked_preflight"
            report["failure_type"] = type(exc).__name__
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            _write_checkpoint(stream, report)
            return report


def _decimal_argument(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError("Expected a positive USD amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise argparse.ArgumentTypeError("Expected a positive USD amount")
    return amount


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Enable paid model inference"
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Check account model availability without invoking a model",
    )
    parser.add_argument("--max-cost-usd", type=_decimal_argument)
    parser.add_argument("--pricing-file", type=Path, default=PRICING_PATH)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--resume-from",
        type=Path,
        help="Resume unattempted scenarios from a compatible partial capture",
    )
    args = parser.parse_args()
    if args.live == args.preflight_only:
        parser.error("Select exactly one of --live or --preflight-only")
    if args.live and args.max_cost_usd is None:
        parser.error("--live requires --max-cost-usd after separate owner approval")
    if args.preflight_only and args.max_cost_usd is not None:
        parser.error("--preflight-only does not accept a paid-run budget")
    load_project_aws_environment()
    if args.live:
        report = asyncio.run(
            run_comparison(
                output=args.output,
                max_cost_usd=args.max_cost_usd,
                pricing_path=args.pricing_file,
                resume_from=args.resume_from,
            )
        )
    else:
        report = preflight_report(output=args.output, pricing_path=args.pricing_file)
    if report.get("status") == "blocked_retrieval_readiness":
        readiness = report["retrieval_readiness"]
        failure_type = readiness.get("failure_type", "unknown local retrieval error")
        missing_module = readiness.get("missing_module")
        if isinstance(missing_module, str):
            failure_type = f"{failure_type}; missing {missing_module}"
        print(
            f"Local policy retrieval is not ready ({failure_type}). "
            "Check the local policy dependencies, cached E5 model and existing "
            "index using the repository README. No new model inference request "
            "was sent.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
