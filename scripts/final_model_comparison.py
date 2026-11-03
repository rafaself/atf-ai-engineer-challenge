"""Standalone issue #82 measurement run; no inference without --live and approval."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import shutil
from contextlib import AsyncExitStack
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Any

import boto3  # type: ignore[import-untyped]
import httpx
from botocore.config import Config  # type: ignore[import-untyped]
from emporio_music import paths
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.settings import AgentSettings
from emporio_music.application.chat import ChatService
from emporio_music.domain.conversations import HistoryLimits
from emporio_music.infrastructure.conversations import SQLiteConversationRepository
from emporio_music.infrastructure.policy_embeddings import E5_MODEL, E5_REVISION
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.infrastructure.sqlite_repository import SQLiteProductRepository
from emporio_music.policies.search import LocalPolicySearch
from emporio_music_api.app import create_app
from huggingface_hub import snapshot_download
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

from scripts.compare_models import (
    Candidate,
    _code_freeze,
    _copy_policy_inputs,
    _execution_failure_category,
    _sha256,
    _tool_calls,
    _tree_sha256,
    estimate_usage_cost,
    load_project_aws_environment,
    load_scenarios,
    request_reservation_usd,
)
from scripts.evaluation_support import RecordingAgent, sanitized

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "docs/benchmarks/final-model-comparison"
IDENTITY = "standalone-final-model-comparison-82-v1"
KEYS = (
    "nova_micro",
    "nova_lite",
    "nemotron_nano_3_30b",
    "nemotron_super_3_120b",
    "gpt_oss_20b",
    "gpt_oss_120b",
    "qwen3_32b",
    "claude_haiku_5_5",
    "gpt6_luna",
    "gpt6_1_sol",
)
PREFLIGHT_PROMPT = (
    "Confira no catálogo o preço e o estoque do Yamaha C40 Nylon Natural."
)
INPUT_LIMIT = 2_000_000  # Includes preflight; identical independently enforced ceiling.
REQUEST_LIMIT = 6
OUTPUT_LIMIT = 1024
HARD_CAP = Decimal("10.00")
OVERHEAD = 2048


def write_json(path: Path, value: Any, *, exclusive: bool = False) -> None:
    """Publish final artifacts exclusively; replace only the working checkpoint."""
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if exclusive:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(text)
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def load_candidates(*, today: date | None = None) -> list[Candidate]:
    """Validate this roster directly, without historical runner restrictions."""
    manifest = json.loads((DIRECTORY / "models.json").read_text())
    if (manifest["region"], manifest["service_tier"], manifest["currency"]) != (
        "us-east-1",
        "standard",
        "USD",
    ):
        raise ValueError("Final benchmark requires us-east-1 Standard USD rates")
    for field in ("checked_at_utc", "endpoint_tool_checked_at_utc"):
        if date.fromisoformat(manifest[field][:10]) != (
            today or datetime.now(UTC).date()
        ):
            raise ValueError("Reverify all ten routes and prices on the run date")
    if tuple(entry["key"] for entry in manifest["models"]) != KEYS:
        raise ValueError("The full ten-candidate roster and canonical order are fixed")
    candidates = []
    fields = Candidate.__dataclass_fields__
    for entry in manifest["models"]:
        if (entry["inference_endpoint"], entry["inference_api"]) != (
            "bedrock-runtime",
            "converse",
        ) or entry["rate_status"] != "verified":
            raise ValueError("Every candidate needs a verified Runtime Converse route")
        values = {key: value for key, value in entry.items() if key in fields}
        for key in values:
            if "usd_per_million" in key:
                values[key] = Decimal(str(values[key]))
                if not values[key].is_finite() or values[key] <= 0:
                    raise ValueError("Rates must be finite and positive")
        candidates.append(Candidate(**values))
    return candidates


def schedule(scenarios: list[dict[str, Any]]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for index, scenario in enumerate(scenarios):
        keys = list(KEYS)
        random.Random(20261103 + index).shuffle(keys)
        result.extend((str(scenario["id"]), key) for key in keys)
    return result


def budget_envelope(candidates: list[Candidate]) -> dict[str, Any]:
    amounts = {}
    for candidate in candidates:
        input_rate = max(
            candidate.input_usd_per_million,
            candidate.cache_write_usd_per_million or Decimal(0),
        )
        amounts[candidate.key] = str(
            (
                INPUT_LIMIT * input_rate
                + 27 * REQUEST_LIMIT * OUTPUT_LIMIT * candidate.output_usd_per_million
            )
            / Decimal(1_000_000)
        )
    return {
        "input_upper_bound_per_candidate_including_preflight": INPUT_LIMIT,
        "input_upper_bound_method": "serialized UTF-8 request bytes + 2048 tokens",
        "maximum_requests_per_candidate_including_preflight": 27 * REQUEST_LIMIT,
        "maximum_output_tokens_per_request": OUTPUT_LIMIT,
        "per_candidate_usd": amounts,
        "total_usd": str(sum(map(Decimal, amounts.values()), Decimal(0))),
        "rate_tier": "short context; enforced before transmission for every request",
    }


def source_freeze(*, require_clean: bool = True) -> dict[str, Any]:
    code = _code_freeze()
    if require_clean and code["working_tree_dirty"]:
        raise ValueError(
            "Commit the selected source revision before readiness/inference"
        )
    files = [
        p
        for base in (ROOT / "packages", ROOT / "apps/api/src", ROOT / "scripts")
        for p in base.rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    files += list(DIRECTORY.glob("*.md")) + list(DIRECTORY.glob("*.json"))
    files += [ROOT / "uv.lock", ROOT / "pyproject.toml"]
    files += [
        ROOT / relative
        for relative in (
            "packages/emporio_music/pyproject.toml",
            "apps/api/pyproject.toml",
            "apps/cli/pyproject.toml",
        )
    ]
    files += list((ROOT / "data").glob("*.csv"))
    files += [
        ROOT / "data/store_policies.pdf",
        paths.CATALOG_DATABASE_PATH,
        paths.OPERATIONS_DATABASE_PATH,
    ]
    files += list((ROOT / "data/policies").rglob("*"))
    hashes = {
        str(p.relative_to(ROOT)): _sha256(p) for p in sorted(set(files)) if p.is_file()
    }
    weights = Path(
        snapshot_download(E5_MODEL, revision=E5_REVISION, local_files_only=True)
    )
    weight_hashes = {
        str(p.relative_to(weights)): _sha256(p)
        for p in sorted(weights.rglob("*"))
        if p.is_file()
    }
    if not weight_hashes or not (paths.DATA_DIRECTORY / "policy-indexes").is_dir():
        raise ValueError(
            "Prepare the existing cached E5 weights and policy index first"
        )
    return {
        "application": code,
        "files_sha256": hashes,
        "index_tree_sha256": _tree_sha256(paths.DATA_DIRECTORY / "policy-indexes"),
        "e5_revision": E5_REVISION,
        "e5_files_sha256": weight_hashes,
    }


def validate_resume(
    report: dict[str, Any], freeze: dict[str, Any], cap: Decimal
) -> None:
    if report.get("benchmark") != IDENTITY or report.get("source_freeze") != freeze:
        raise ValueError("Resume must match this experiment and exact source freeze")
    if Decimal(str(report.get("approved_max_cost_usd", "0"))) != cap or report.get(
        "budget_fault"
    ):
        raise ValueError(
            "Resume approval changed or prior accounting fault needs resolution"
        )
    if tuple(report.get("models", {})) != KEYS:
        raise ValueError("Resume roster differs")
    scenarios = load_scenarios(DIRECTORY / "scenarios.json")
    for model in report["models"].values():
        if [case["scenario_id"] for case in model["scenarios"]] != [
            s["id"] for s in scenarios
        ]:
            raise ValueError("Resume scenario set differs")
        for case, scenario in zip(model["scenarios"], scenarios, strict=True):
            if [t["prompt"] for t in case["turns"]] != [
                t["message"] for t in scenario["turns"]
            ]:
                raise ValueError("Resume question sequence differs")
    for attempt in report.get("provider_attempts", []):
        amount = Decimal(attempt["accounted_usd"])
        if not amount.is_finite() or amount < 0:
            raise ValueError("Invalid resumed spend")
    if (
        sum(
            (Decimal(a["accounted_usd"]) for a in report["provider_attempts"]),
            Decimal(0),
        )
        > cap
    ):
        raise ValueError("Prior attempts already exceed the approved cap")


class BudgetFault(RuntimeError):
    """Stop globally before additional provider calls when accounting is unsafe."""


class Ledger:
    def __init__(self, report: dict[str, Any], checkpoint: Path, cap: Decimal) -> None:
        self.report = report
        self.checkpoint = checkpoint
        self.cap = cap
        self.lock = RLock()
        self.active: tuple[Candidate, str, str, int] | None = None
        self.candidates: dict[str, Candidate] = {}
        self.verify_inputs: Any = lambda: None

    def save(self) -> None:
        with self.lock:
            self.report["estimated_spend_usd"] = str(
                sum(
                    (
                        Decimal(a["accounted_usd"])
                        for a in self.report["provider_attempts"]
                    ),
                    Decimal(0),
                )
            )
            write_json(self.checkpoint, self.report)

    def stop(self, reason: str) -> None:
        self.report.setdefault("budget_fault", reason)
        self.save()
        raise BudgetFault(reason)

    def before_call(self, **kwargs: Any) -> None:
        with self.lock:
            if self.report.get("budget_fault") or self.active is None:
                self.stop("missing_or_faulted_run_context")
            assert self.active is not None
            candidate, phase, scenario, turn = self.active
            self.candidates[candidate.key] = candidate
            self.verify_inputs()
            body = kwargs.get("params", {}).get("body")
            if not isinstance(body, (bytes, str)):
                self.stop("serialized_request_unavailable")
            encoded = body.encode() if isinstance(body, str) else body
            bound = len(encoded) + OVERHEAD
            sent = json.loads(encoded)
            limit = min(
                candidate.context_window_tokens,
                candidate.long_context_threshold_tokens
                or candidate.context_window_tokens,
            )
            attempts = self.report["provider_attempts"]
            previous = [a for a in attempts if a["model_key"] == candidate.key]
            same_turn = [
                a
                for a in previous
                if (a["phase"], a["scenario_id"], a["turn_index"])
                == (phase, scenario, turn)
            ]
            if (
                bound > limit
                or sum(a["input_upper_bound"] for a in previous) + bound > INPUT_LIMIT
                or len(previous) >= 27 * REQUEST_LIMIT
                or len(same_turn) >= REQUEST_LIMIT
                or sent.get("inferenceConfig", {}).get("maxTokens") != OUTPUT_LIMIT
            ):
                self.stop("request_or_input_envelope_exceeded")
            reserve = request_reservation_usd(
                candidate, OUTPUT_LIMIT, input_tokens=bound
            )
            spent = sum((Decimal(a["accounted_usd"]) for a in attempts), Decimal(0))
            if spent + reserve > self.cap:
                self.stop("approved_spend_cap")
            attempt = {
                "model_key": candidate.key,
                "phase": phase,
                "scenario_id": scenario,
                "turn_index": turn,
                "status": "in_flight",
                "input_upper_bound": bound,
                "reserved_usd": str(reserve),
                "accounted_usd": str(reserve),
                "requested_settings": {"max_tokens": OUTPUT_LIMIT, "temperature": 0},
                "serialized_settings": {
                    key: sent[key]
                    for key in (
                        "inferenceConfig",
                        "additionalModelRequestFields",
                        "serviceTier",
                    )
                    if key in sent
                },
            }
            kwargs["context"]["final_benchmark_attempt"] = len(attempts)
            attempts.append(attempt)
            self.save()  # Durable reservation BEFORE network transmission.

    def after_call(self, **kwargs: Any) -> None:
        with self.lock:
            index = kwargs.get("context", {}).get("final_benchmark_attempt")
            if index is None:
                self.stop("untracked_provider_response")
            attempt = self.report["provider_attempts"][index]
            parsed = kwargs.get("parsed", {})
            raw = parsed.get("usage")
            attempt["status"] = "returned"
            if isinstance(raw, dict) and all(
                type(raw.get(key)) is int and raw[key] >= 0
                for key in ("inputTokens", "outputTokens")
            ):
                read = raw.get("cacheReadInputTokens", 0)
                write = raw.get("cacheWriteInputTokens", 0)
                if any(type(value) is not int or value < 0 for value in (read, write)):
                    self.stop("invalid_cache_usage")
                usage = {
                    "input_tokens": raw["inputTokens"] + read + write,
                    "output_tokens": raw["outputTokens"],
                    "cache_read_tokens": read,
                    "cache_write_tokens": write,
                }
                attempt["usage"] = usage
                cost, _ = estimate_usage_cost(
                    self.candidates[attempt["model_key"]],
                    {"usage": {"responses": [usage]}},
                    observed_requests=1,
                    max_output_tokens=OUTPUT_LIMIT,
                )
                if (
                    usage["input_tokens"] > attempt["input_upper_bound"]
                    or usage["output_tokens"] > OUTPUT_LIMIT
                    or cost > Decimal(attempt["reserved_usd"])
                ):
                    attempt["accounted_usd"] = str(
                        max(cost, Decimal(attempt["reserved_usd"]))
                    )
                    self.stop("provider_usage_exceeded_reservation")
                attempt["accounted_usd"] = str(cost)
            else:
                attempt["usage"] = None  # Keep the entire bounded reservation.
            self.save()


def candidate_settings(candidate: Candidate) -> AgentSettings:
    return AgentSettings(
        model_id=candidate.inference_model_id,
        aws_region="us-east-1",
        aws_profile=os.environ.get("AWS_PROFILE"),
        request_timeout_seconds=15,
        max_requests=6,
        max_tool_calls=5,
        max_output_tokens=1024,
    )


def client_for(
    candidate: Candidate, ledger: Ledger, search: LocalPolicySearch, work: Path
) -> tuple[httpx.AsyncClient, RecordingAgent]:
    settings = candidate_settings(candidate)
    sdk = boto3.Session(
        profile_name=settings.aws_profile, region_name="us-east-1"
    ).client(
        "bedrock-runtime",
        config=Config(
            connect_timeout=5,
            read_timeout=15,
            retries={"mode": "standard", "total_max_attempts": 1},
        ),
    )
    sdk.meta.events.register("before-call.bedrock-runtime.Converse", ledger.before_call)
    sdk.meta.events.register("after-call.bedrock-runtime.Converse", ledger.after_call)
    model = BedrockConverseModel(
        candidate.inference_model_id, provider=BedrockProvider(bedrock_client=sdk)
    )
    recorder = RecordingAgent(
        create_store_agent(
            settings,
            SQLiteProductRepository(paths.CATALOG_DATABASE_PATH),
            SQLiteOrderRepository(paths.OPERATIONS_DATABASE_PATH),
            model=model,
            policy_search=search,
        )
    )
    service = ChatService(
        recorder,
        SQLiteConversationRepository(work / f"{candidate.key}.sqlite3"),
        timeout_seconds=60,
        history_limits=HistoryLimits(),
    )
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(
            app=create_app(service), raise_app_exceptions=False
        ),
        base_url="http://final-benchmark.local",
    )
    return client, recorder


async def run_turn(
    client: httpx.AsyncClient,
    recorder: RecordingAgent,
    ledger: Ledger,
    candidate: Candidate,
    phase: str,
    scenario: dict[str, Any],
    turn_index: int,
    record: dict[str, Any],
    session_id: str | None,
) -> str | None:
    payload = dict(scenario["turns"][turn_index])
    record.update(prompt=payload["message"], status="in_flight")
    if "customer_id" in scenario:
        payload["customer_id"] = scenario["customer_id"]
    if session_id:
        payload["session_id"] = session_id
    ledger.active = (candidate, phase, scenario["id"], turn_index)
    ledger.save()
    started = perf_counter()
    recorder.evidence = {}
    transport_failure = None
    try:
        response = await client.post("/api/chat", json=payload)
        body = response.json()
        http_status: int | None = response.status_code
    except Exception as exc:
        body = {"detail": "Evaluation HTTP request failed"}
        http_status = None
        transport_failure = type(exc).__name__
    record["end_to_end_latency_seconds"] = round(perf_counter() - started, 6)
    if not isinstance(body, dict):
        body = {"detail": "Unexpected HTTP response shape"}
    returned_session = body.pop("session_id", None)
    complete = (
        http_status == 200
        and isinstance(returned_session, str)
        and bool(body.get("answer"))
    )
    evidence = sanitized(recorder.evidence)
    record.update(
        status="completed" if complete else "failed",
        http_status=http_status,
        http_response=body,
        model_trace=evidence,
        tool_calls=_tool_calls(evidence),
    )
    turn_attempts = [
        a
        for a in ledger.report["provider_attempts"]
        if (a["model_key"], a["phase"], a["scenario_id"], a["turn_index"])
        == (candidate.key, phase, scenario["id"], turn_index)
    ]
    if evidence.get("usage", {}).get("requests", 0) > len(turn_attempts):
        ledger.report["budget_fault"] = "untracked_model_response"
    record["provider_attempts"] = len(turn_attempts)
    record["output_validation_retries"] = sum(
        part.get("part_kind") == "retry-prompt"
        for message in evidence.get("messages", [])
        for part in message.get("parts", [])
    )
    if not complete:
        record["failure_category"] = _execution_failure_category(
            http_status, evidence, transport_failure
        )
        if ledger.report.get("budget_fault"):
            record["failure_category"] = "budget_accounting"
    for attempt in ledger.report["provider_attempts"]:
        if (
            attempt["model_key"],
            attempt["phase"],
            attempt["scenario_id"],
            attempt["turn_index"],
        ) == (candidate.key, phase, scenario["id"], turn_index) and attempt[
            "status"
        ] == "in_flight":
            # Could be a terminated network call or a still-running SDK worker.
            attempt["status"] = "usage_unknown"
            if http_status == 504:
                ledger.report["budget_fault"] = "provider_request_pending_after_timeout"
    ledger.active = None
    ledger.save()
    return returned_session if complete else None


def preflight_success(record: dict[str, Any]) -> bool:
    messages = record.get("model_trace", {}).get("messages", [])
    calls = [
        p
        for m in messages
        for p in m.get("parts", [])
        if p.get("part_kind") == "tool-call"
    ]
    returns = [
        p
        for m in messages
        for p in m.get("parts", [])
        if p.get("part_kind") == "tool-return"
    ]

    def successful_result(part: dict[str, Any]) -> bool:
        content = part.get("content")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except ValueError:
                return False
        return isinstance(content, dict) and bool(
            content.get("products") or content.get("product")
        )

    return (
        record.get("status") == "completed"
        and any(
            c.get("tool_name")
            in {
                "find_product_by_name",
                "search_available_products",
                "get_product_details",
            }
            and any(
                r.get("tool_call_id") == c.get("tool_call_id") and successful_result(r)
                for r in returns
            )
            for c in calls
        )
        and record.get("model_trace", {}).get("usage", {}).get("requests", 0) >= 2
    )


def mark_interrupted(report: dict[str, Any]) -> None:
    """Never retry an attempted conversation after losing its ephemeral session."""
    for model in report["models"].values():
        for case in [model["preflight"], *model["scenarios"]]:
            attempted = any(t["status"] != "not_executed" for t in case["turns"])
            if attempted and case["status"] in {"running", "not_executed"}:
                case["status"] = (
                    "completed"
                    if all(t["status"] == "completed" for t in case["turns"])
                    else "failed"
                )
                for turn in case["turns"]:
                    if turn["status"] == "in_flight":
                        turn.update(status="failed", failure_category="interrupted")
    for attempt in report["provider_attempts"]:
        if attempt["status"] == "in_flight":
            attempt["status"] = "usage_unknown"


def initial_report(
    candidates: list[Candidate],
    scenarios: list[dict[str, Any]],
    freeze: dict[str, Any],
    cap: Decimal,
    approval: str,
) -> dict[str, Any]:
    def case(value: dict[str, Any]) -> dict[str, Any]:
        return {
            "scenario_id": value["id"],
            "status": "not_executed",
            "expected": value.get("expected", {}),
            "customer_id": value.get("customer_id"),
            "turns": [
                {"turn_index": i, "prompt": t.get("message"), "status": "not_executed"}
                for i, t in enumerate(value["turns"])
            ],
        }

    return {
        "benchmark": IDENTITY,
        "issue": 82,
        "status": "running",
        "approved_max_cost_usd": str(cap),
        "approval_note": approval,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "source_freeze": freeze,
        "budget": budget_envelope(candidates),
        "provider_attempts": [],
        "schedule": schedule(scenarios),
        "models": {
            c.key: {
                "model": json.loads(json.dumps(asdict(c), default=str)),
                "status": "pending",
                "preflight": case({"id": "preflight", "turns": [{}]}),
                "scenarios": [case(s) for s in scenarios],
            }
            for c in candidates
        },
    }


def input_stamps() -> dict[Path, tuple[int, int]]:
    weights = Path(
        snapshot_download(E5_MODEL, revision=E5_REVISION, local_files_only=True)
    )
    sources = [
        ROOT / "packages",
        ROOT / "apps/api/src",
        ROOT / "scripts",
        ROOT / "data",
        weights,
        DIRECTORY,
    ]
    files = [
        p
        for root in sources
        for p in root.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and "benchmark-cache" not in p.parts
    ]
    files += [ROOT / "uv.lock", ROOT / "pyproject.toml"]
    files += [
        ROOT / relative
        for relative in ("apps/api/pyproject.toml", "apps/cli/pyproject.toml")
    ]
    return {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in files}


async def execute(
    work: Path, *, cap: Decimal | None = None, approval: str = "", resume: bool = False
) -> dict[str, Any]:
    candidates = load_candidates()
    scenarios = load_scenarios(DIRECTORY / "scenarios.json")
    if len(scenarios) != 16 or sum(len(s["turns"]) for s in scenarios) != 26:
        raise ValueError("The final workload is fixed at 16 conversations / 26 turns")
    envelope = budget_envelope(candidates)
    if Decimal(envelope["total_usd"]) > HARD_CAP:
        raise ValueError("The full-run envelope exceeds the proposed US$10 ceiling")
    if cap is not None and (
        not cap.is_finite()
        or not Decimal(envelope["total_usd"]) <= cap <= HARD_CAP
        or not approval.strip()
    ):
        raise ValueError(
            "Record explicit approval of a cap covering the full envelope, up to US$10"
        )
    freeze = source_freeze()
    work.mkdir(parents=True, exist_ok=True)
    if work.is_relative_to(ROOT):
        raise ValueError(
            "Use a working directory outside the checkout to keep the source freeze clean"
        )
    if cap is not None and any(
        (work / name).exists() for name in ("capture.json", "preflight.json")
    ):
        raise ValueError("Final artifacts already exist; this run is immutable")
    policy_dir = work / "policy-data"
    if policy_dir.exists():
        shutil.rmtree(policy_dir)
    _copy_policy_inputs(policy_dir)
    started = perf_counter()
    search = LocalPolicySearch(data_directory=policy_dir)
    evidence = search.search("horário de funcionamento da loja")
    if not evidence["records"]:
        raise ValueError("Policy retrieval returned no readiness evidence")
    readiness = {
        "benchmark": IDENTITY,
        "status": "ready_without_inference",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "source_freeze": freeze,
        "budget": envelope,
        "policy_cold_start_seconds": round(perf_counter() - started, 6),
        "requested_settings": {
            "read_timeout": 15,
            "chat_timeout": 60,
            "max_requests": REQUEST_LIMIT,
            "max_tool_calls": 5,
            "max_output_tokens": OUTPUT_LIMIT,
            "temperature": 0,
            "sdk_attempts": 1,
            "history": HistoryLimits().model_dump(),
        },
        "paid_calls": 0,
    }
    write_json(work / "readiness.json", readiness)
    if cap is None:
        return readiness
    checkpoint = work / "checkpoint.json"
    if resume:
        report: dict[str, Any] = json.loads(checkpoint.read_text())
        validate_resume(report, freeze, cap)
        mark_interrupted(report)
    else:
        if checkpoint.exists():
            raise ValueError(
                "Existing run; use --resume or choose a fresh work directory"
            )
        report = initial_report(candidates, scenarios, freeze, cap, approval)
    report["readiness"] = readiness
    ledger = Ledger(report, checkpoint, cap)
    stamps = input_stamps()

    def verify() -> None:
        if _code_freeze() != freeze["application"]:
            ledger.stop("frozen_source_revision_changed")
        for path, previous in stamps.items():
            if (
                not path.exists()
                or (path.stat().st_size, path.stat().st_mtime_ns) != previous
            ):
                ledger.stop("frozen_input_changed")

    ledger.verify_inputs = verify
    ledger.save()
    lookup = {c.key: c for c in candidates}
    async with AsyncExitStack() as stack:
        clients = {}
        for candidate in candidates:
            try:
                client, recorder = client_for(candidate, ledger, search, work)
                await stack.enter_async_context(client)
                clients[candidate.key] = (client, recorder)
            except Exception as exc:
                report["models"][candidate.key].update(
                    status="excluded_preflight", failure_type=type(exc).__name__
                )
            ledger.save()
        # No model is scored until all feasible routes have the same bounded tool preflight.
        for candidate in candidates:
            model_report = report["models"][candidate.key]
            if (
                candidate.key not in clients
                or model_report["status"] == "excluded_preflight"
            ):
                continue
            case = model_report["preflight"]
            if case["status"] == "not_executed":
                await run_turn(
                    *clients[candidate.key],
                    ledger,
                    candidate,
                    "preflight",
                    {"id": "preflight", "turns": [{"message": PREFLIGHT_PROMPT}]},
                    0,
                    case["turns"][0],
                    None,
                )
                attempts = [
                    a
                    for a in report["provider_attempts"]
                    if a["model_key"] == candidate.key and a["phase"] == "preflight"
                ]
                valid = (
                    preflight_success(case["turns"][0])
                    and bool(attempts)
                    and all(a.get("usage") for a in attempts)
                )
                case["status"] = "completed" if valid else "failed"
            model_report["status"] = (
                "ready" if case["status"] == "completed" else "excluded_preflight"
            )
            if model_report["status"] == "excluded_preflight":
                model_report["exclusion_category"] = case["turns"][0].get(
                    "failure_category", "tool_roundtrip_or_usage_not_demonstrated"
                )
            ledger.save()
            if report.get("budget_fault"):
                break
        for scenario_id, key in schedule(scenarios):
            if report.get("budget_fault"):
                break
            model_report = report["models"][key]
            if model_report["status"] != "ready":
                continue
            scenario = next(s for s in scenarios if s["id"] == scenario_id)
            case = next(
                s for s in model_report["scenarios"] if s["scenario_id"] == scenario_id
            )
            if case["status"] != "not_executed":
                continue
            case["status"] = "running"
            session = None
            for index, record in enumerate(case["turns"]):
                session = await run_turn(
                    *clients[key],
                    ledger,
                    lookup[key],
                    "main",
                    scenario,
                    index,
                    record,
                    session,
                )
                print(
                    f"{key} {scenario_id} turn {index + 1}: {record['status']}",
                    flush=True,
                )
                if record["status"] != "completed" or report.get("budget_fault"):
                    error = (
                        record.get("model_trace", {})
                        .get("failure", {})
                        .get("aws_error_code")
                    )
                    if error in {"AccessDeniedException", "ResourceNotFoundException"}:
                        model_report["status"] = "route_unavailable"
                    break
            case["status"] = (
                "completed"
                if all(t["status"] == "completed" for t in case["turns"])
                else "failed"
            )
            ledger.save()
    report["status"] = (
        "stopped_accounting_fault"
        if report.get("budget_fault")
        else "captured_pending_human_review"
    )
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    for model_report in report["models"].values():
        if model_report["status"] == "ready":
            model_report["status"] = (
                "completed"
                if all(c["status"] == "completed" for c in model_report["scenarios"])
                else "completed_with_failures_or_missing_turns"
            )
    ledger.save()
    write_json(work / "capture.json", sanitized(report), exclusive=True)
    write_json(
        work / "preflight.json",
        {
            "benchmark": IDENTITY,
            "models": {
                key: value["preflight"] for key, value in report["models"].items()
            },
            "provider_attempts": [
                a for a in report["provider_attempts"] if a["phase"] == "preflight"
            ],
        },
        exclusive=True,
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-cost-usd", type=Decimal)
    parser.add_argument("--approval-note", default="")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.live != (args.max_cost_usd is not None) or (not args.live and args.resume):
        parser.error(
            "Paid execution requires --live, --max-cost-usd and --approval-note"
        )
    load_project_aws_environment()
    report = asyncio.run(
        execute(
            args.work_dir.resolve(),
            cap=args.max_cost_usd,
            approval=args.approval_note,
            resume=args.resume,
        )
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "budget": report["budget"],
                "estimated_spend_usd": report.get("estimated_spend_usd", "0"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
