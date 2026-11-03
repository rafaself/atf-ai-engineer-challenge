"""Evaluate two Nemotron models on the approved holiday follow-up conversation."""

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
from emporio_music.agent.settings import AgentSettings, load_agent_settings
from emporio_music.application.chat import ChatService
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_api.app import create_app

from scripts.compare_models import (
    ENDPOINT_RUNTIME,
    EXPECTED_SETTINGS,
    Candidate,
    RequestCounter,
    _check_local_retrieval_readiness,
    _copy_policy_inputs,
    _model_executor,
    _runtime_chat_settings,
    _sha256,
    _tool_calls,
    freeze_inputs,
    load_project_aws_environment,
    request_reservation_usd,
    turn_reservation_usd,
)
from scripts.validate_us18 import RecordingAgent, sanitized

PROJECT_ROOT = Path.cwd().resolve()
PRICING_PATH = PROJECT_ROOT / "docs/examples/grounding-followups/nemotron-pricing.json"
MAX_APPROVAL_USD = Decimal("0.60")
PRIOR_ATTEMPT_RESERVE_USD = Decimal("0.19532800")
PRIOR_ATTEMPT_EVIDENCE = (
    "docs/examples/grounding-followups/nemotron-capture-2026-11-02.json"
)
MAX_OUTPUT_TOKENS = int(EXPECTED_SETTINGS["max_output_tokens"])
MAX_REQUESTS = 3
MAX_TOOL_CALLS = int(EXPECTED_SETTINGS["max_tool_calls"])
TURNS = (
    "Qual é o horário normal de funcionamento da loja?",
    "E nos feriados e no Natal, há atendimento?",
)


def _load_candidates(today: date | None = None) -> list[Candidate]:
    document = json.loads(PRICING_PATH.read_text(encoding="utf-8"))
    if (
        document.get("region") != "us-east-1"
        or document.get("currency") != "USD"
        or document.get("service_tier") != "standard"
        or document.get("verified") is not True
        or not document.get("source_url")
        or date.fromisoformat(str(document.get("checked_at_utc", "")))
        != (today or datetime.now(UTC).date())
    ):
        raise ValueError("Refresh and verify model prices for today's run")
    candidates: list[Candidate] = []
    entries = document.get("models")
    if not isinstance(entries, list) or len(entries) != 2:
        raise ValueError("The focused benchmark requires exactly two models")
    for entry in entries:
        model_id = str(entry["model_id"])
        if entry.get("inference_endpoint") != ENDPOINT_RUNTIME:
            raise ValueError(f"Unsupported endpoint for {model_id}")
        if entry.get("inference_api") != "converse":
            raise ValueError(f"Unsupported API for {model_id}")
        if int(entry["context_window_tokens"]) != 256_000:
            raise ValueError(f"Refresh the context limit for {model_id}")
        candidates.append(
            Candidate(
                key=str(entry["key"]),
                model_id=model_id,
                inference_endpoint=ENDPOINT_RUNTIME,
                inference_model_id=model_id,
                inference_api="converse",
                context_window_tokens=int(entry["context_window_tokens"]),
                input_usd_per_million=Decimal(str(entry["input_usd_per_million"])),
                output_usd_per_million=Decimal(str(entry["output_usd_per_million"])),
                tool_use_status=str(entry["tool_use_status"]),
            )
        )
    if any(
        candidate.input_usd_per_million <= 0 or candidate.output_usd_per_million <= 0
        for candidate in candidates
    ):
        raise ValueError("Verified token rates must be positive")
    expected_ids = {
        "nvidia.nemotron-super-3-120b",
        "nvidia.nemotron-nano-3-30b",
    }
    if {candidate.model_id for candidate in candidates} != expected_ids:
        raise ValueError("The focused benchmark model IDs do not match the request")
    return candidates


def _retrieval_preflight() -> dict[str, Any]:
    readiness = _check_local_retrieval_readiness()
    if readiness.get("status") != "ready":
        return readiness
    from emporio_music.policies.search import LocalPolicySearch

    search = LocalPolicySearch(data_directory=paths.DATA_DIRECTORY)
    queries = {
        "turn_1": TURNS[0],
        "turn_2_if_retrieved": f"{TURNS[0]}\n{TURNS[1]}",
    }
    results = {name: search.search(query) for name, query in queries.items()}
    for result in results.values():
        records = result.get("records", [])
        if result.get("status") != "evidence_found" or not records:
            return {"status": "blocked", "failure_type": "HolidayPolicyEvidenceMissing"}
        if not any(
            "Natal" in str(record.get("text", ""))
            and "pode ser estendido" in str(record.get("text", ""))
            for record in records
        ):
            return {
                "status": "blocked",
                "failure_type": "ChristmasQualificationMissing",
            }
    return {"status": "ready", "results": results}


def _input_freeze() -> dict[str, Any]:
    freeze = freeze_inputs()
    freeze["focused_scenario"] = {
        "id": "holiday-hours-two-turn",
        "turns": list(TURNS),
        "sha256": hashlib.sha256(
            json.dumps(TURNS, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
    }
    freeze["focused_pricing_sha256"] = _sha256(PRICING_PATH)
    return freeze


def _planned_reservation(candidates: list[Candidate]) -> Decimal:
    return sum(
        (
            turn_reservation_usd(candidate, max_requests=MAX_REQUESTS) * len(TURNS)
            for candidate in candidates
        ),
        Decimal(0),
    )


def _bounded_turn_cost(
    candidate: Candidate,
    evidence: dict[str, Any],
    observed_requests: int,
    max_output_tokens: int,
) -> tuple[Decimal, dict[str, object]]:
    """Price provider responses and reserve calls whose usage was not recorded.

    Conversation history is present in the recording context with zero-token
    response objects. Count only response entries with positive token usage so
    history cannot make an unreported provider response appear billed at zero.
    """
    responses = evidence.get("usage", {}).get("responses", [])
    measured = [
        item
        for item in responses
        if isinstance(item, dict)
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
    ]
    input_tokens = sum(int(item.get("input_tokens") or 0) for item in measured)
    output_tokens = sum(int(item.get("output_tokens") or 0) for item in measured)
    known_cost = (
        Decimal(input_tokens) * candidate.input_usd_per_million
        + Decimal(output_tokens) * candidate.output_usd_per_million
    ) / Decimal(1_000_000)
    missing = max(0, observed_requests - len(measured))
    cost = known_cost + missing * request_reservation_usd(candidate, max_output_tokens)
    return cost, {
        "requests_observed": observed_requests,
        "requests_with_usage": len(measured),
        "requests_with_missing_usage": missing,
        "input_tokens_reported": input_tokens,
        "output_tokens_reported": output_tokens,
        "estimated_usd": str(cost),
        "cache_read_tokens": evidence.get("usage", {}).get("cache_read_tokens"),
        "cache_write_tokens": evidence.get("usage", {}).get("cache_write_tokens"),
        "reasoning_tokens": evidence.get("usage", {}).get("reasoning_tokens"),
        "cost_note": (
            "Positive-token responses are priced at current standard rates; "
            "unreported calls reserve full model context and output cap."
        ),
    }


def preflight(output: Path) -> dict[str, Any]:
    candidates = _load_candidates()
    retrieval = _retrieval_preflight()
    planned_reservation = _planned_reservation(candidates)
    remaining_cap = MAX_APPROVAL_USD - PRIOR_ATTEMPT_RESERVE_USD
    aggregate_reservation = PRIOR_ATTEMPT_RESERVE_USD + planned_reservation
    report: dict[str, Any] = {
        "issue": 43,
        "purpose": "Focused two-model holiday policy evaluation",
        "status": "ready_no_paid_calls"
        if retrieval.get("status") == "ready"
        and planned_reservation <= remaining_cap
        and aggregate_reservation <= MAX_APPROVAL_USD
        else "blocked_preflight",
        "region": "us-east-1",
        "paid_calls": 0,
        "pricing_file": PRICING_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "pricing_manifest_sha256": _sha256(PRICING_PATH),
        "source_freeze": _input_freeze(),
        "turns": list(TURNS),
        "retrieval_preflight": retrieval,
        "runtime_limits": {
            "request_timeout_seconds": EXPECTED_SETTINGS["request_timeout_seconds"],
            "max_requests_per_http_turn": MAX_REQUESTS,
            "max_tool_calls_per_http_turn": MAX_TOOL_CALLS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        "maximum_provider_requests": len(candidates) * len(TURNS) * MAX_REQUESTS,
        "approved_max_cost_usd": str(MAX_APPROVAL_USD),
        "prior_attempt_reserved_upper_usd": str(PRIOR_ATTEMPT_RESERVE_USD),
        "prior_attempt_evidence": PRIOR_ATTEMPT_EVIDENCE,
        "current_run_worst_case_reserved_usd": str(
            planned_reservation.quantize(Decimal("0.00000001"))
        ),
        "aggregate_worst_case_reserved_usd": str(
            aggregate_reservation.quantize(Decimal("0.00000001"))
        ),
        "remaining_cap_for_current_run_usd": str(remaining_cap),
        "models": [
            {
                "model_id": candidate.model_id,
                "endpoint": candidate.inference_endpoint,
                "api": candidate.inference_api,
                "context_window_tokens": candidate.context_window_tokens,
                "input_usd_per_million": str(candidate.input_usd_per_million),
                "output_usd_per_million": str(candidate.output_usd_per_million),
                "tool_use_status": candidate.tool_use_status,
                "worst_case_usd": str(
                    (
                        turn_reservation_usd(candidate, max_requests=MAX_REQUESTS)
                        * len(TURNS)
                    ).quantize(Decimal("0.00000001"))
                ),
            }
            for candidate in candidates
        ],
        "evaluation_dimensions": {
            "tool_use": (
                "Search policy on turn one. On turn two, reuse only if the prior "
                "answer retained the relevant rule and qualification; otherwise retrieve."
            ),
            "answer_faithfulness": (
                "State normal holiday closure and possible special-date extensions; "
                "do not assert the specific Christmas schedule without evidence."
            ),
        },
        "finished_at_utc": datetime.now(UTC).isoformat(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


async def run_live(output: Path, cap: Decimal) -> dict[str, Any]:
    if not cap.is_finite() or cap <= 0 or cap > MAX_APPROVAL_USD:
        raise ValueError("The approved cap must be positive and at most US$0.60")
    candidates = _load_candidates()
    retrieval = _retrieval_preflight()
    if retrieval.get("status") != "ready":
        raise RuntimeError("Local policy retrieval is not ready")
    settings = load_agent_settings()
    if (
        settings.request_timeout_seconds != EXPECTED_SETTINGS["request_timeout_seconds"]
        or settings.max_tool_calls != EXPECTED_SETTINGS["max_tool_calls"]
        or settings.max_output_tokens != EXPECTED_SETTINGS["max_output_tokens"]
    ):
        raise ValueError(
            "The focused run requires the prepared timeout and output limits"
        )
    chat_timeout, history_limits = _runtime_chat_settings()
    planned_reservation = _planned_reservation(candidates)
    remaining_cap = cap - PRIOR_ATTEMPT_RESERVE_USD
    aggregate_reservation = PRIOR_ATTEMPT_RESERVE_USD + planned_reservation
    if planned_reservation > remaining_cap or aggregate_reservation > cap:
        raise ValueError("Prior attempt reserve plus this run exceeds the approved cap")
    report: dict[str, Any] = {
        "issue": 43,
        "purpose": "Focused two-model holiday policy evaluation",
        "status": "running",
        "region": "us-east-1",
        "paid_calls": 0,
        "estimated_spend_usd": "0",
        "approved_max_cost_usd": str(cap),
        "prior_attempt_reserved_upper_usd": str(PRIOR_ATTEMPT_RESERVE_USD),
        "prior_attempt_evidence": PRIOR_ATTEMPT_EVIDENCE,
        "pricing_file": PRICING_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "pricing_manifest_sha256": _sha256(PRICING_PATH),
        "current_run_worst_case_reserved_usd": str(
            planned_reservation.quantize(Decimal("0.00000001"))
        ),
        "aggregate_worst_case_reserved_usd": str(
            aggregate_reservation.quantize(Decimal("0.00000001"))
        ),
        "remaining_cap_for_current_run_usd": str(remaining_cap),
        "maximum_provider_requests": len(candidates) * len(TURNS) * MAX_REQUESTS,
        "runtime_limits": {
            "request_timeout_seconds": EXPECTED_SETTINGS["request_timeout_seconds"],
            "max_requests_per_http_turn": MAX_REQUESTS,
            "max_tool_calls_per_http_turn": MAX_TOOL_CALLS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        },
        "source_freeze": _input_freeze(),
        "retrieval_preflight": retrieval,
        "turns": list(TURNS),
        "evaluation_dimensions": {
            "tool_use": (
                "Search policy on turn one. On turn two, reuse only if the prior "
                "answer retained the relevant rule and qualification; otherwise retrieve."
            ),
            "answer_faithfulness": (
                "State normal holiday closure and possible special-date extensions; "
                "do not assert the specific Christmas schedule without evidence."
            ),
        },
        "model_runs": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        total_estimated_cost = Decimal(0)
        for candidate in candidates:
            counter = RequestCounter()
            model_settings = AgentSettings(
                model_id=candidate.inference_model_id,
                aws_region="us-east-1",
                aws_profile=settings.aws_profile,
                request_timeout_seconds=settings.request_timeout_seconds,
                max_requests=MAX_REQUESTS,
                max_tool_calls=settings.max_tool_calls,
                max_output_tokens=settings.max_output_tokens,
            )
            model_run: dict[str, Any] = {
                "model_id": candidate.model_id,
                "endpoint": candidate.inference_endpoint,
                "api": candidate.inference_api,
                "context_window_tokens": candidate.context_window_tokens,
                "input_usd_per_million": str(candidate.input_usd_per_million),
                "output_usd_per_million": str(candidate.output_usd_per_million),
                "tool_use_status": candidate.tool_use_status,
                "status": "running",
                "turns": [],
            }
            report["model_runs"].append(model_run)
            with tempfile.TemporaryDirectory(prefix="nemotron-holiday-") as tempdir:
                temp_root = Path(tempdir)
                try:
                    policy_data = _copy_policy_inputs(temp_root / "policy-data")
                    executor = _model_executor(
                        candidate, model_settings, counter, policy_data
                    )
                except Exception as exc:
                    model_run["status"] = "provider_setup_failed"
                    model_run["failure_type"] = type(exc).__name__
                    continue
                recorder = RecordingAgent(executor)
                service = ChatService(
                    recorder,
                    SQLiteConversationRepository(temp_root / "conversations.sqlite3"),
                    timeout_seconds=chat_timeout,
                    history_limits=history_limits,
                )
                app = create_app(service)
                session_id: str | None = None
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                    base_url="http://nemotron-holiday.local",
                ) as client:
                    for index, prompt in enumerate(TURNS, start=1):
                        reservation = turn_reservation_usd(
                            candidate,
                            max_requests=MAX_REQUESTS,
                            max_output_tokens=settings.max_output_tokens,
                        )
                        if total_estimated_cost + reservation > remaining_cap:
                            model_run["status"] = "stopped_at_budget_cap"
                            report["status"] = "stopped_at_budget_cap"
                            break
                        count_before = counter.count
                        started = perf_counter()
                        payload: dict[str, str] = {"message": prompt}
                        if session_id is not None:
                            payload["session_id"] = session_id
                        failure_type: str | None = None
                        try:
                            posted_response = await client.post(
                                "/api/chat", json=payload
                            )
                        except Exception as exc:
                            response = None
                            elapsed = round(perf_counter() - started, 3)
                            body = {"detail": "Evaluation request failed"}
                            failure_type = type(exc).__name__
                        else:
                            response = posted_response
                            elapsed = round(perf_counter() - started, 3)
                            try:
                                body = posted_response.json()
                            except ValueError:
                                body = {"detail": "HTTP response was not JSON"}
                        if not isinstance(body, dict):
                            body = {"detail": "HTTP response JSON was not an object"}
                        if response is not None and 200 <= response.status_code < 300:
                            returned_session = body.pop("session_id", None)
                            if isinstance(returned_session, str):
                                session_id = returned_session
                                turn_status = "completed"
                            else:
                                turn_status = "failed"
                        else:
                            body.pop("session_id", None)
                            turn_status = "failed"
                        evidence = sanitized(recorder.evidence)
                        observed = counter.count - count_before
                        usage_requests = evidence.get("usage", {}).get("requests", 0)
                        request_count = max(
                            observed,
                            int(usage_requests)
                            if isinstance(usage_requests, int)
                            else 0,
                        )
                        turn_cost, usage = _bounded_turn_cost(
                            candidate,
                            evidence,
                            request_count,
                            settings.max_output_tokens,
                        )
                        if response is None and request_count == 0:
                            turn_cost = reservation
                            usage["requests_with_missing_usage"] = MAX_REQUESTS
                            usage["cost_note"] = (
                                "No provider request count was available; held the "
                                "full HTTP-turn reservation against the cap."
                            )
                        total_estimated_cost += turn_cost
                        report["paid_calls"] += request_count
                        report["estimated_spend_usd"] = str(total_estimated_cost)
                        turn_record: dict[str, Any] = {
                            "turn_index": index,
                            "prompt": prompt,
                            "status": turn_status,
                            "http_status": response.status_code
                            if response is not None
                            else None,
                            "end_to_end_latency_seconds": elapsed,
                            "model_api_requests": request_count,
                            "reservation_upper_usd": str(
                                reservation.quantize(Decimal("0.00000001"))
                            ),
                            "usage": usage,
                            "tool_calls": _tool_calls(evidence),
                            "http_response": body,
                            "model_trace": evidence,
                        }
                        if failure_type is not None:
                            turn_record["transport_failure_type"] = failure_type
                        model_run["turns"].append(turn_record)
                        _write(report, stream)
                        if turn_status != "completed":
                            model_run["status"] = "failed"
                            model_run["turns"].extend(
                                {"turn_index": remaining, "status": "not_executed"}
                                for remaining in range(index + 1, len(TURNS) + 1)
                            )
                            break
                    else:
                        model_run["status"] = "completed"
            _write(report, stream)
        if report.get("status") == "running":
            report["status"] = (
                "completed"
                if all(
                    item.get("status") == "completed" for item in report["model_runs"]
                )
                else "completed_with_failures"
            )
        report["aggregate_estimated_or_reserved_usd"] = str(
            (PRIOR_ATTEMPT_RESERVE_USD + total_estimated_cost).quantize(
                Decimal("0.00000001")
            )
        )
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
        parser.error("--live requires a separately approved --max-cost-usd")
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
                "status": report.get("status"),
                "paid_calls": report.get("paid_calls", 0),
                "current_run_worst_case_reserved_usd": report.get(
                    "current_run_worst_case_reserved_usd"
                ),
                "aggregate_worst_case_reserved_usd": report.get(
                    "aggregate_worst_case_reserved_usd"
                ),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    if report.get("status") not in {"ready_no_paid_calls", "completed"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
