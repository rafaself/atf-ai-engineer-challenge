"""Shared, deterministic helpers used by the two retained benchmark runners.

The published benchmark source freezes identify their original implementations.
Changes here apply only to new runs; recorded captures remain immutable.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from emporio_music import paths

ROOT = Path(__file__).resolve().parents[1]
AWS_ENVIRONMENT_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_DEFAULT_REGION",
    "AWS_REGION",
    "AWS_PROFILE",
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
    long_context_threshold_tokens: int | None = None
    long_context_input_usd_per_million: Decimal | None = None
    long_context_output_usd_per_million: Decimal | None = None
    cache_write_usd_per_million: Decimal | None = None
    long_context_cache_write_usd_per_million: Decimal | None = None


def load_project_aws_environment() -> None:
    """Load project AWS settings without printing their values."""
    values = dotenv_values(ROOT / ".env", verbose=False)
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
        ROOT / "packages/emporio_music/src",
        ROOT / "apps/api/src",
        ROOT / "apps/cli/src",
        ROOT / "scripts",
    )
    files = sorted(
        path
        for root in source_roots
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    file_hashes = {
        path.relative_to(ROOT).as_posix(): _sha256(path) for path in files
    }
    status = subprocess.run(
        ["git", "status", "--short"],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        cwd=ROOT,
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


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    scenarios = document.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Scenario fixture must contain conversations")
    if len(scenarios) != document.get("scenario_count"):
        raise ValueError("Scenario count differs from the fixture declaration")
    if any(not item.get("turns") for item in scenarios):
        raise ValueError("Every conversation needs at least one turn")
    if sum(len(item["turns"]) for item in scenarios) != document.get(
        "planned_turns_per_model"
    ):
        raise ValueError("Turn count differs from the fixture declaration")
    if len({item.get("id") for item in scenarios}) != len(scenarios):
        raise ValueError("Scenario IDs must be unique")
    return scenarios


def _token_rates(
    candidate: Candidate, input_tokens: int
) -> tuple[Decimal, Decimal, Decimal | None]:
    if (
        candidate.long_context_threshold_tokens is not None
        and input_tokens > candidate.long_context_threshold_tokens
    ):
        assert candidate.long_context_input_usd_per_million is not None
        assert candidate.long_context_output_usd_per_million is not None
        return (
            candidate.long_context_input_usd_per_million,
            candidate.long_context_output_usd_per_million,
            candidate.long_context_cache_write_usd_per_million,
        )
    return (
        candidate.input_usd_per_million,
        candidate.output_usd_per_million,
        candidate.cache_write_usd_per_million,
    )


def request_reservation_usd(
    candidate: Candidate,
    max_output_tokens: int,
    *,
    input_tokens: int | None = None,
) -> Decimal:
    reserved_input_tokens = (
        candidate.context_window_tokens if input_tokens is None else input_tokens
    )
    input_rate, output_rate, write_rate = _token_rates(candidate, reserved_input_tokens)
    return (
        reserved_input_tokens * max(input_rate, write_rate or input_rate)
        + max_output_tokens * output_rate
    ) / Decimal(1_000_000)


def benchmark_request_input_limit(candidate: Candidate) -> int:
    """Keep each request inside the model context and any short-context tier."""
    return min(
        candidate.context_window_tokens,
        candidate.long_context_threshold_tokens or candidate.context_window_tokens,
    )


def estimate_usage_cost(
    candidate: Candidate,
    evidence: dict[str, Any],
    *,
    observed_requests: int,
    max_output_tokens: int,
    request_input_upper_bounds: tuple[int, ...] = (),
) -> tuple[Decimal, dict[str, object]]:
    """Estimate usage and reserve each unreported request at its bounded input size."""
    usage = evidence.get("usage", {})
    responses = usage.get("responses", [])
    known_cost = Decimal(0)
    complete = 0
    known_input = 0
    known_output = 0
    missing_usage_requests = 0
    request_count = max(observed_requests, len(responses))
    fallback_input_limit = benchmark_request_input_limit(candidate)
    for index in range(request_count):
        response = responses[index] if index < len(responses) else {}
        input_tokens = response.get("input_tokens")
        output_tokens = response.get("output_tokens")
        if input_tokens is None or output_tokens is None:
            input_bound = (
                request_input_upper_bounds[index]
                if index < len(request_input_upper_bounds)
                else fallback_input_limit
            )
            known_cost += request_reservation_usd(
                candidate,
                max_output_tokens,
                input_tokens=input_bound,
            )
            missing_usage_requests += 1
            continue
        input_count = int(input_tokens)
        output_count = int(output_tokens)
        known_input += input_count
        known_output += output_count
        input_rate, output_rate, write_rate = _token_rates(candidate, input_count)
        cache_write_count = int(response.get("cache_write_tokens") or 0)
        # SDK input totals include cache tokens. Charge reads at full input rates
        # conservatively; include any documented implicit cache-creation premium.
        write_premium = cache_write_count * max(
            Decimal(0), (write_rate or input_rate) - input_rate
        )
        known_cost += (
            input_count * input_rate + output_count * output_rate + write_premium
        ) / Decimal(1_000_000)
        complete += 1

    estimated_cost = known_cost
    return estimated_cost, {
        "requests_observed": request_count,
        "requests_with_usage": complete,
        "requests_with_missing_usage": missing_usage_requests,
        "input_tokens_reported": known_input if complete else None,
        "output_tokens_reported": known_output if complete else None,
        "estimated_usd": str(estimated_cost.quantize(Decimal("0.00000001"))),
    }


def _copy_policy_inputs(target: Path) -> Path:
    """Copy the frozen policy inputs so Chroma can only touch a temporary index."""
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(paths.DATA_DIRECTORY / "policies", target / "policies")
    shutil.copy2(paths.DATA_DIRECTORY / "store_policies.pdf", target)
    shutil.copytree(paths.DATA_DIRECTORY / "policy-indexes", target / "policy-indexes")
    return target


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
