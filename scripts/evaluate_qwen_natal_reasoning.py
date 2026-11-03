"""Run a bounded Qwen holiday-answer and evidence-summary probe."""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from emporio_music.agent.settings import load_agent_settings
from emporio_music.application.chat import ChatService
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music.policies.search import LocalPolicySearch
from emporio_music_api.app import create_app

from scripts.compare_models import (
    Candidate,
    RequestCounter,
    _copy_policy_inputs,
    _model_executor,
    _runtime_chat_settings,
    _tool_calls,
    _validate_agent_limits,
    estimate_usage_cost,
    freeze_inputs,
    load_project_aws_environment,
    load_verified_candidates,
    turn_reservation_usd,
)
from scripts.validate_us18 import RecordingAgent, sanitized

PROJECT_ROOT = Path.cwd().resolve()
FIXTURE_PATH = (
    PROJECT_ROOT
    / "docs/examples/model-comparison/scenarios-qwen-natal-reasoning-v1.json"
)
PRICING_PATH = PROJECT_ROOT / "docs/examples/model-comparison/pricing.json"
OUTPUT_CAP_USD = Decimal("1.00")
MODEL_KEY = "qwen3_32b"


def load_turns() -> tuple[dict[str, Any], list[str]]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    scenarios = fixture.get("scenarios")
    if (
        fixture.get("issue") != 43
        or fixture.get("scenario_count") != 1
        or not isinstance(scenarios, list)
        or len(scenarios) != 1
    ):
        raise ValueError("The focused Qwen fixture is invalid")
    turns = scenarios[0].get("turns")
    expected_count = fixture.get("planned_turns_per_model")
    if (
        not isinstance(turns, list)
        or type(expected_count) is not int
        or len(turns) != expected_count
        or any(not isinstance(item.get("message"), str) for item in turns)
    ):
        raise ValueError("The focused Qwen turn list is invalid")
    return fixture, [item["message"] for item in turns]


def retrieval_preflight() -> dict[str, object]:
    result = LocalPolicySearch().search(
        "horário normal nos feriados e possível extensão no Natal"
    )
    records = result.get("records", [])
    if result.get("status") != "evidence_found" or not any(
        record.get("id") == "policy-v2.1-s2"
        and record.get("source") == "store_policies.pdf"
        and 2 in record.get("pages", [])
        and "Natal" in str(record.get("text", ""))
        and "pode ser estendido" in str(record.get("text", ""))
        for record in records
    ):
        return {"status": "blocked", "reason": "holiday_qualification_missing"}
    return {
        "status": "ready",
        "record_ids": [record.get("id") for record in records],
    }


def prepare_report() -> dict[str, Any]:
    fixture, turns = load_turns()
    candidate = load_verified_candidates(PRICING_PATH, model_keys=(MODEL_KEY,))[0]
    retrieval = retrieval_preflight()
    return {
        "issue": 43,
        "purpose": "Qwen policy prompt experiment with post-answer evidence-summary probe",
        "status": "ready_no_paid_calls"
        if retrieval.get("status") == "ready"
        else "blocked_preflight",
        "region": "us-east-1",
        "model_id": candidate.model_id,
        "fixture": FIXTURE_PATH.relative_to(PROJECT_ROOT).as_posix(),
        "source_freeze": freeze_inputs(FIXTURE_PATH),
        "turns": turns,
        "rationale_probe_note": (
            "A concise evidence summary is requested; generated explanation is not proof of private internal reasoning."
        ),
        "retrieval_preflight": retrieval,
        "paid_calls": 0,
        "estimated_spend_usd": "0",
        "preflight_at_utc": datetime.now(UTC).isoformat(),
        "fixture_metadata": {
            "scenario_count": fixture["scenario_count"],
            "planned_turns_per_model": fixture["planned_turns_per_model"],
        },
    }


async def run_live(output: Path, cap: Decimal) -> dict[str, Any]:
    report = prepare_report()
    if report["status"] != "ready_no_paid_calls":
        raise ValueError("Local policy retrieval is not ready for the rationale probe")
    if not cap.is_finite() or cap <= 0 or cap > OUTPUT_CAP_USD:
        raise ValueError("The evaluation cap must be between US$0 and US$1")

    candidate: Candidate = load_verified_candidates(
        PRICING_PATH, model_keys=(MODEL_KEY,)
    )[0]
    settings = load_agent_settings()
    _validate_agent_limits(settings)
    chat_timeout, history_limits = _runtime_chat_settings()
    turns = report["turns"]
    maximum_reserve = turn_reservation_usd(
        candidate,
        max_requests=settings.max_requests,
        max_output_tokens=settings.max_output_tokens,
    ) * len(turns)
    if maximum_reserve > cap:
        raise ValueError(
            f"Cap does not cover the maximum four-turn reservation of {maximum_reserve}"
        )

    report.update(
        {
            "status": "running",
            "approved_max_cost_usd": str(cap),
            "maximum_reserve_usd": str(maximum_reserve.quantize(Decimal("0.00000001"))),
            "runtime_settings": {
                "request_timeout_seconds": settings.request_timeout_seconds,
                "max_requests_per_turn": settings.max_requests,
                "max_tool_calls_per_turn": settings.max_tool_calls,
                "max_output_tokens": settings.max_output_tokens,
            },
            "turn_results": [],
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        _write(report, stream)
        counter = RequestCounter()
        with tempfile.TemporaryDirectory(prefix="qwen-natal-reasoning-") as tmp:
            temporary = Path(tmp)
            policy_data = _copy_policy_inputs(temporary / "policy-data")
            executor = _model_executor(candidate, settings, counter, policy_data)
            recorder = RecordingAgent(executor)
            service = ChatService(
                recorder,
                SQLiteConversationRepository(temporary / "conversations.sqlite3"),
                timeout_seconds=chat_timeout,
                history_limits=history_limits,
            )
            app = create_app(service)
            session_id: str | None = None
            total_cost = Decimal(0)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://qwen-natal-reasoning.local",
            ) as client:
                for turn_index, prompt in enumerate(turns, start=1):
                    reserve = turn_reservation_usd(
                        candidate,
                        max_requests=settings.max_requests,
                        max_output_tokens=settings.max_output_tokens,
                    )
                    if total_cost + reserve > cap:
                        report["status"] = "stopped_at_budget_cap"
                        break
                    count_before = counter.count
                    started = perf_counter()
                    payload: dict[str, str] = {"message": prompt}
                    if session_id is not None:
                        payload["session_id"] = session_id
                    try:
                        response = await client.post("/api/chat", json=payload)
                        body = response.json()
                        failure_type = None
                    except Exception as exc:
                        response = None
                        body = {"detail": "Evaluation request failed"}
                        failure_type = type(exc).__name__
                    elapsed = round(perf_counter() - started, 3)
                    if not isinstance(body, dict):
                        body = {"detail": "Evaluation response was not an object"}
                    returned_session = body.pop("session_id", None)
                    if (
                        response is not None
                        and response.is_success
                        and isinstance(returned_session, str)
                    ):
                        session_id = returned_session
                        status = "completed"
                    else:
                        status = "failed"

                    evidence = sanitized(recorder.evidence)
                    observed = counter.count - count_before
                    cost, usage = estimate_usage_cost(
                        candidate,
                        evidence,
                        observed_requests=observed,
                        max_output_tokens=settings.max_output_tokens,
                    )
                    total_cost += cost
                    result: dict[str, Any] = {
                        "turn_index": turn_index,
                        "prompt": prompt,
                        "status": status,
                        "http_status": response.status_code if response else None,
                        "end_to_end_latency_seconds": elapsed,
                        "provider_requests_observed": observed,
                        "usage": usage,
                        "tool_calls": _tool_calls(evidence),
                        "http_response": body,
                        "model_trace": evidence,
                    }
                    if failure_type is not None:
                        result["transport_failure_type"] = failure_type
                    report["turn_results"].append(result)
                    report["paid_calls"] = counter.count
                    report["estimated_spend_usd"] = str(
                        total_cost.quantize(Decimal("0.00000001"))
                    )
                    report["status"] = (
                        "running"
                        if status == "completed"
                        else "completed_with_failures"
                    )
                    _write(report, stream)
                    if status != "completed":
                        break

        if report["status"] == "running":
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
        parser.error("--live requires a separately approved --max-cost-usd")
    if args.preflight_only and args.max_cost_usd is not None:
        parser.error("--preflight-only does not accept a paid-run cap")
    load_project_aws_environment()
    if args.live:
        report = asyncio.run(run_live(args.output, args.max_cost_usd))
    else:
        report = prepare_report()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            _write(report, stream)
    print(
        json.dumps(
            {
                "status": report["status"],
                "paid_calls": report.get("paid_calls", 0),
                "maximum_reserve_usd": report.get("maximum_reserve_usd"),
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    if report["status"] not in {"ready_no_paid_calls", "completed"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
