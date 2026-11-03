"""Evaluate Nova 2 Lite on the bounded holiday-policy follow-up."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from emporio_music import paths
from emporio_music.agent.settings import load_agent_settings
from emporio_music.application.chat import ChatService
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_api.app import create_app

from scripts.compare_models import (
    ENDPOINT_RUNTIME,
    Candidate,
    RequestCounter,
    _copy_policy_inputs,
    _model_executor,
    _runtime_chat_settings,
    _sha256,
    _tool_calls,
    freeze_inputs,
    load_project_aws_environment,
)
from scripts.validate_us18 import RecordingAgent, sanitized

PROJECT_ROOT = Path.cwd().resolve()
PRICING_PATH = PROJECT_ROOT / "docs/examples/grounding-followups/nova2-pricing.json"
PREVIOUS_CAPTURE = (
    PROJECT_ROOT / "docs/examples/grounding-followups/nova2-capture-2026-11-02.json"
)
APPROVED_CAP_USD = Decimal("1.00")
MODEL_ID = "amazon.nova-2-lite-v1:0"
INFERENCE_MODEL_ID = "us.amazon.nova-2-lite-v1:0"
INPUT_USD_PER_MILLION = Decimal("0.33")
OUTPUT_USD_PER_MILLION = Decimal("2.75")
CONTEXT_WINDOW_TOKENS = 1_000_000
MAX_OUTPUT_TOKENS = 1024
MAX_REQUESTS_PER_TURN = 2
MAX_REQUESTS_TOTAL = 4
MAX_REQUEST_BODY_BYTES = 65_536
INPUT_TOKEN_RESERVE = MAX_REQUEST_BODY_BYTES * 4
PRICE_RESERVE_MULTIPLIER = Decimal("2")
TURNS = (
    "Qual é o horário normal de funcionamento da loja?",
    "E nos feriados e no Natal, há atendimento?",
)


class RequestBudgetExceeded(RuntimeError):
    """Reject an over-budget request before sending it to Bedrock."""


class BoundedRequestCounter(RequestCounter):
    def __init__(self) -> None:
        super().__init__()
        self.body_sizes: list[int] = []

    def before_call(self, params: object = None, **_kwargs: object) -> None:
        if self.count >= MAX_REQUESTS_TOTAL:
            raise RequestBudgetExceeded("Total Nova 2 request limit reached")
        if not isinstance(params, dict):
            raise RequestBudgetExceeded("Bedrock request size cannot be verified")
        body = params.get("body")
        if isinstance(body, str):
            body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            body_bytes = body
        else:
            raise RequestBudgetExceeded("Bedrock request size cannot be verified")
        body_size = len(body_bytes)
        if body_size > MAX_REQUEST_BODY_BYTES:
            raise RequestBudgetExceeded("Bedrock request exceeds the byte limit")
        self.body_sizes.append(body_size)
        self.count += 1


def _candidate(today: date | None = None) -> Candidate:
    document = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    if (
        document.get("model_id") != MODEL_ID
        or document.get("inference_model_id") != INFERENCE_MODEL_ID
        or document.get("inference_endpoint") != ENDPOINT_RUNTIME
        or document.get("inference_api") != "converse"
        or document.get("region") != "us-east-1"
        or document.get("currency") != "USD"
        or document.get("service_tier") != "standard"
        or int(document.get("context_window_tokens", 0)) != CONTEXT_WINDOW_TOKENS
        or Decimal(str(document.get("input_usd_per_million", "0")))
        != INPUT_USD_PER_MILLION
        or Decimal(str(document.get("output_usd_per_million", "0")))
        != OUTPUT_USD_PER_MILLION
        or date.fromisoformat(str(document.get("checked_at_utc", "")))
        != (today or datetime.now(UTC).date())
    ):
        raise ValueError("Nova 2 route and prices must be refreshed for this run")
    return Candidate(
        key="nova_2_lite",
        model_id=MODEL_ID,
        inference_endpoint=ENDPOINT_RUNTIME,
        inference_model_id=INFERENCE_MODEL_ID,
        inference_api="converse",
        context_window_tokens=CONTEXT_WINDOW_TOKENS,
        input_usd_per_million=INPUT_USD_PER_MILLION,
        output_usd_per_million=OUTPUT_USD_PER_MILLION,
        tool_use_status="client_side_tool_calling_documented",
    )


def _retrieval_preflight() -> dict[str, Any]:
    from emporio_music.policies.search import LocalPolicySearch

    search = LocalPolicySearch(data_directory=paths.DATA_DIRECTORY)
    results = {
        "turn_1": search.search(TURNS[0]),
        "turn_2_with_context": search.search(f"{TURNS[0]}\n{TURNS[1]}"),
    }
    for result in results.values():
        if result.get("status") != "evidence_found":
            return {"status": "blocked", "failure_type": "HolidayPolicyMissing"}
        records = result.get("records", [])
        if not any(
            record.get("id") == "policy-v2.1-s2"
            and record.get("source") == "store_policies.pdf"
            and 2 in record.get("pages", [])
            and "Natal" in str(record.get("text", ""))
            and "pode ser estendido" in str(record.get("text", ""))
            for record in records
        ):
            return {
                "status": "blocked",
                "failure_type": "ChristmasQualificationMissing",
            }
    return {"status": "ready", "results": results}


def _reservation_per_request(candidate: Candidate) -> Decimal:
    return (
        Decimal(INPUT_TOKEN_RESERVE)
        * candidate.input_usd_per_million
        * PRICE_RESERVE_MULTIPLIER
        + Decimal(MAX_OUTPUT_TOKENS)
        * candidate.output_usd_per_million
        * PRICE_RESERVE_MULTIPLIER
    ) / Decimal(1_000_000)


def _maximum_reserve(candidate: Candidate) -> Decimal:
    return _reservation_per_request(candidate) * MAX_REQUESTS_TOTAL


def _previous_attempt() -> dict[str, Any]:
    if not PREVIOUS_CAPTURE.exists():
        return {"capture": None, "paid_calls_observed": 0, "reserve_usd": "0"}
    report = json.loads(PREVIOUS_CAPTURE.read_text(encoding="utf-8"))
    reserve = Decimal(str(report.get("estimated_or_reserved_usd", "0")))
    calls = int(report.get("paid_calls", 0))
    return {
        "capture": PREVIOUS_CAPTURE.relative_to(PROJECT_ROOT).as_posix(),
        "paid_calls_observed": calls,
        "reserve_usd": str(reserve),
    }


def _turn_cost(
    candidate: Candidate,
    evidence: dict[str, Any],
    observed_requests: int,
) -> tuple[Decimal, dict[str, Any]]:
    responses = evidence.get("usage", {}).get("responses", [])
    measured = [
        item
        for item in responses
        if isinstance(item, dict)
        and isinstance(item.get("input_tokens"), int)
        and isinstance(item.get("output_tokens"), int)
        and any(
            isinstance(item.get(field), int) and item[field] > 0
            for field in (
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "reasoning_tokens",
            )
        )
    ]
    reported_input_tokens = sum(int(item.get("input_tokens") or 0) for item in measured)
    cache_tokens = sum(
        int(item.get("cache_read_tokens") or 0)
        + int(item.get("cache_write_tokens") or 0)
        for item in measured
    )
    input_tokens = reported_input_tokens + cache_tokens
    output_tokens = sum(int(item.get("output_tokens") or 0) for item in measured)
    known_cost = (
        Decimal(input_tokens) * candidate.input_usd_per_million
        + Decimal(output_tokens) * candidate.output_usd_per_million
    ) / Decimal(1_000_000)
    missing = max(0, observed_requests - len(measured))
    reserve = _reservation_per_request(candidate) * missing
    return known_cost + reserve, {
        "requests_observed": observed_requests,
        "responses_with_positive_usage": len(measured),
        "requests_with_missing_usage": missing,
        "input_tokens_reported": reported_input_tokens,
        "input_tokens_costed_at_full_rate": input_tokens,
        "output_tokens_reported": output_tokens,
        "missing_request_reserve_usd": str(reserve),
        "estimated_or_reserved_usd": str(known_cost + reserve),
    }


def _source_freeze() -> dict[str, Any]:
    freeze = freeze_inputs()
    freeze["scenario"] = {
        "id": "holiday-hours-two-turn",
        "turns": list(TURNS),
        "sha256": hashlib.sha256(
            json.dumps(TURNS, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
    }
    freeze["pricing_sha256"] = _sha256(PRICING_PATH)
    return freeze


def preflight(output: Path) -> dict[str, Any]:
    candidate = _candidate()
    retrieval = _retrieval_preflight()
    maximum_reserve = _maximum_reserve(candidate)
    previous = _previous_attempt()
    prior_reserve = Decimal(str(previous["reserve_usd"]))
    aggregate_reserve = prior_reserve + maximum_reserve
    report: dict[str, Any] = {
        "issue": 43,
        "purpose": "Single-model Nova 2 Lite holiday follow-up smoke evaluation",
        "status": "ready_no_paid_calls"
        if retrieval.get("status") == "ready" and aggregate_reserve <= APPROVED_CAP_USD
        else "blocked_preflight",
        "region": "us-east-1",
        "paid_calls": 0,
        "previous_attempt": previous,
        "model_id": MODEL_ID,
        "inference_model_id": INFERENCE_MODEL_ID,
        "pricing_file": PRICING_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "maximum_provider_requests": MAX_REQUESTS_TOTAL,
        "request_body_max_bytes": MAX_REQUEST_BODY_BYTES,
        "input_tokens_reserved_per_request": INPUT_TOKEN_RESERVE,
        "price_reserve_multiplier": str(PRICE_RESERVE_MULTIPLIER),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "approved_budget_usd": str(APPROVED_CAP_USD),
        "worst_case_reserve_usd": str(maximum_reserve.quantize(Decimal("0.00000001"))),
        "aggregate_worst_case_reserve_usd": str(
            aggregate_reserve.quantize(Decimal("0.00000001"))
        ),
        "source_freeze": _source_freeze(),
        "retrieval_preflight": retrieval,
        "turns": list(TURNS),
        "finished_at_utc": datetime.now(UTC).isoformat(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


async def run_live(output: Path, cap: Decimal) -> dict[str, Any]:
    candidate = _candidate()
    retrieval = _retrieval_preflight()
    if retrieval.get("status") != "ready":
        raise ValueError("Local holiday policy retrieval is not ready")
    reserve = _maximum_reserve(candidate)
    previous = _previous_attempt()
    prior_reserve = Decimal(str(previous["reserve_usd"]))
    aggregate_reserve = prior_reserve + reserve
    if cap > APPROVED_CAP_USD or aggregate_reserve > cap:
        raise ValueError(
            "Approved cap must cover prior and current reserves and be at most US$1"
        )

    settings = load_agent_settings()
    if settings.max_tool_calls < 1 or settings.max_output_tokens != MAX_OUTPUT_TOKENS:
        raise ValueError("Nova 2 run requires the current harness tool/output limits")
    settings = settings.model_copy(
        update={
            "model_id": INFERENCE_MODEL_ID,
            "max_requests": MAX_REQUESTS_PER_TURN,
        }
    )
    chat_timeout, history_limits = _runtime_chat_settings()
    report: dict[str, Any] = {
        "issue": 43,
        "purpose": "Single-model Nova 2 Lite holiday follow-up smoke evaluation",
        "status": "running",
        "region": "us-east-1",
        "model_id": MODEL_ID,
        "inference_model_id": INFERENCE_MODEL_ID,
        "endpoint": ENDPOINT_RUNTIME,
        "api": "converse",
        "context_window_tokens": CONTEXT_WINDOW_TOKENS,
        "input_usd_per_million": str(candidate.input_usd_per_million),
        "output_usd_per_million": str(candidate.output_usd_per_million),
        "approved_budget_usd": str(cap),
        "previous_attempt": previous,
        "worst_case_reserve_usd": str(reserve.quantize(Decimal("0.00000001"))),
        "aggregate_worst_case_reserve_usd": str(
            aggregate_reserve.quantize(Decimal("0.00000001"))
        ),
        "remaining_budget_after_prior_reserve_usd": str(cap - prior_reserve),
        "maximum_provider_requests": MAX_REQUESTS_TOTAL,
        "request_body_max_bytes": MAX_REQUEST_BODY_BYTES,
        "input_tokens_reserved_per_request": INPUT_TOKEN_RESERVE,
        "price_reserve_multiplier": str(PRICE_RESERVE_MULTIPLIER),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "runtime_limits": {
            "request_timeout_seconds": settings.request_timeout_seconds,
            "max_requests_per_http_turn": MAX_REQUESTS_PER_TURN,
            "max_tool_calls_per_http_turn": settings.max_tool_calls,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        "pricing_file": PRICING_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "pricing_sha256": _sha256(PRICING_PATH),
        "source_freeze": _source_freeze(),
        "retrieval_preflight": retrieval,
        "turns": list(TURNS),
        "tool_choice_criteria": (
            "Search policy on the first turn. Reuse the earlier answer on follow-up "
            "only if it preserves the normal closure and special-date qualification."
        ),
        "faithfulness_criteria": (
            "State the normal holiday closure and possible special-date extension; "
            "do not confirm Christmas opening or closure without a specific schedule."
        ),
        "paid_calls": 0,
        "estimated_or_reserved_usd": "0",
        "aggregate_estimated_or_reserved_usd": str(prior_reserve),
        "turn_results": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        counter = BoundedRequestCounter()
        with tempfile.TemporaryDirectory(prefix="nova2-holiday-") as tempdir:
            temporary_root = Path(tempdir)
            policy_data = _copy_policy_inputs(temporary_root / "policy-data")
            executor = _model_executor(candidate, settings, counter, policy_data)
            recorder = RecordingAgent(executor)
            service = ChatService(
                recorder,
                SQLiteConversationRepository(temporary_root / "conversations.sqlite3"),
                timeout_seconds=chat_timeout,
                history_limits=history_limits,
            )
            app = create_app(service)
            session_id: str | None = None
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://nova2-holiday.local",
            ) as client:
                total_estimate = Decimal(0)
                for turn_index, prompt in enumerate(TURNS, start=1):
                    remaining_requests = MAX_REQUESTS_TOTAL - counter.count
                    next_turn_reserve = _reservation_per_request(candidate) * min(
                        MAX_REQUESTS_PER_TURN, remaining_requests
                    )
                    if prior_reserve + total_estimate + next_turn_reserve > cap:
                        report["status"] = "stopped_at_budget_cap"
                        break
                    count_before = counter.count
                    body_before = len(counter.body_sizes)
                    started = perf_counter()
                    payload: dict[str, str] = {"message": prompt}
                    if session_id is not None:
                        payload["session_id"] = session_id
                    failure_type: str | None = None
                    try:
                        response = await client.post("/api/chat", json=payload)
                        http_body = response.json()
                    except Exception as exc:
                        response = None
                        http_body = {"detail": "Evaluation request failed"}
                        failure_type = type(exc).__name__
                    elapsed = round(perf_counter() - started, 3)
                    if not isinstance(http_body, dict):
                        http_body = {"detail": "Evaluation response was not an object"}
                    returned_session = http_body.pop("session_id", None)
                    if (
                        response is not None
                        and response.is_success
                        and isinstance(returned_session, str)
                    ):
                        session_id = returned_session
                        turn_status = "completed"
                    else:
                        turn_status = "failed"
                    evidence = sanitized(recorder.evidence)
                    observed = counter.count - count_before
                    usage_responses = evidence.get("usage", {}).get("responses", [])
                    positive_usage_count = sum(
                        isinstance(item, dict)
                        and any(
                            isinstance(item.get(name), int) and item[name] > 0
                            for name in (
                                "input_tokens",
                                "output_tokens",
                                "cache_read_tokens",
                                "cache_write_tokens",
                                "reasoning_tokens",
                            )
                        )
                        for item in usage_responses
                    )
                    request_count = max(observed, positive_usage_count)
                    cost, usage = _turn_cost(candidate, evidence, request_count)
                    total_estimate += cost
                    report["paid_calls"] += observed
                    report["estimated_or_reserved_usd"] = str(total_estimate)
                    report["aggregate_estimated_or_reserved_usd"] = str(
                        prior_reserve + total_estimate
                    )
                    result: dict[str, Any] = {
                        "turn_index": turn_index,
                        "prompt": prompt,
                        "status": turn_status,
                        "http_status": response.status_code
                        if response is not None
                        else None,
                        "end_to_end_latency_seconds": elapsed,
                        "provider_requests_observed": observed,
                        "request_body_sizes_bytes": counter.body_sizes[body_before:],
                        "usage": usage,
                        "tool_calls": _tool_calls(evidence),
                        "http_response": http_body,
                        "model_trace": evidence,
                    }
                    if failure_type is not None:
                        result["transport_failure_type"] = failure_type
                    report["turn_results"].append(result)
                    _write(report, stream)
                    input_bound_exceeded = any(
                        int(item.get("input_tokens") or 0) > INPUT_TOKEN_RESERVE
                        for item in usage_responses
                        if isinstance(item, dict)
                    )
                    if turn_status != "completed":
                        report["status"] = "completed_with_failures"
                        break
                    if input_bound_exceeded:
                        report["status"] = "stopped_at_input_reserve"
                        break
                else:
                    report["status"] = "completed"
        report["finished_at_utc"] = datetime.now(UTC).isoformat()
        _write(report, stream)
    return report


def _write(report: dict[str, Any], stream: Any) -> None:
    stream.seek(0)
    stream.truncate()
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
    stream.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--live", action="store_true")
    parser.add_argument("--max-cost-usd", type=Decimal)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.live and args.max_cost_usd is None:
        parser.error("--live requires the separately approved --max-cost-usd")
    if args.preflight_only and args.max_cost_usd is not None:
        parser.error("--preflight-only does not accept a paid-run cap")
    load_project_aws_environment()
    report = (
        asyncio.run(run_live(args.output, args.max_cost_usd))
        if args.live
        else preflight(args.output)
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "paid_calls": report.get("paid_calls", 0),
                "worst_case_reserve_usd": report.get("worst_case_reserve_usd"),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    if report["status"] not in {"ready_no_paid_calls", "completed"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
