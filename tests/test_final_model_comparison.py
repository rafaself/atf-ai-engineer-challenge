"""Risk-focused offline contracts for the independent issue #82 experiment."""

import asyncio
import copy
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import boto3  # type: ignore[import-untyped]
import httpx
import pytest
from botocore.awsrequest import AWSResponse  # type: ignore[import-untyped]
from emporio_music import paths
from emporio_music.infrastructure.catalog_import import import_catalog
from emporio_music.policies.search import LocalPolicySearch
from pydantic_ai import models

from scripts.evaluation_support import RecordingAgent
from scripts.final_model_comparison import (
    DIRECTORY,
    KEYS,
    BudgetFault,
    Ledger,
    budget_envelope,
    client_for,
    initial_report,
    load_candidates,
    mark_interrupted,
    preflight_success,
    run_turn,
    schedule,
    validate_resume,
    write_json,
)
from scripts.final_model_review import aggregate, prepare_review


def report() -> dict[str, Any]:
    candidates = load_candidates(today=date(2026, 11, 3))
    scenarios = json.loads((DIRECTORY / "scenarios.json").read_text())["scenarios"]
    return initial_report(
        candidates, scenarios, {}, Decimal("10"), "test-only approval"
    )


def test_full_roster_and_schedule_have_no_historical_baseline_dependency() -> None:
    candidates = load_candidates(today=date(2026, 11, 3))
    value = report()
    assert tuple(c.key for c in candidates) == KEYS
    assert [c.inference_model_id for c in candidates] == [
        "amazon.nova-micro-v1:0",
        "amazon.nova-lite-v1:0",
        "nvidia.nemotron-nano-3-30b",
        "nvidia.nemotron-super-3-120b",
        "openai.gpt-oss-20b-1:0",
        "openai.gpt-oss-120b-1:0",
        "qwen.qwen3-32b-v1:0",
        "us.anthropic.claude-haiku-5-5",
        "us.openai.gpt-6-luna",
        "us.openai.gpt-6.1-sol",
    ]
    assert all(
        c.inference_endpoint == "bedrock-runtime" and c.inference_api == "converse"
        for c in candidates
    )
    order = value["schedule"]
    assert len(order) == 160 and len(set(order)) == 160
    for offset in range(0, 160, 10):
        block = order[offset : offset + 10]
        assert len({scenario for scenario, _ in block}) == 1
        assert {key for _, key in block} == set(KEYS)
    assert order == schedule(
        json.loads((DIRECTORY / "scenarios.json").read_text())["scenarios"]
    )
    assert [key for _, key in order[:10]] != list(KEYS)
    assert budget_envelope(candidates)["total_usd"] == "9.81175456"


def start(ledger: Ledger, *, phase: str = "main") -> dict[str, Any]:
    candidate = load_candidates(today=date(2026, 11, 3))[-1]
    ledger.active = (candidate, phase, "example", 0)
    kwargs = {
        "params": {
            "body": json.dumps(
                {"inferenceConfig": {"maxTokens": 1024, "temperature": 0}}
            ).encode()
        },
        "context": {},
    }
    ledger.before_call(**kwargs)
    return kwargs


def test_provider_reservation_is_durable_before_transmission_and_missing_usage_is_held(
    tmp_path: Path,
) -> None:
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("10"))
    kwargs = start(ledger)
    checkpoint = json.loads(ledger.checkpoint.read_text())
    before = checkpoint["provider_attempts"][0]
    assert before["status"] == "in_flight" and Decimal(before["accounted_usd"]) > 0
    ledger.after_call(context=kwargs["context"], parsed={})
    attempt = ledger.report["provider_attempts"][0]
    assert attempt["usage"] is None
    assert attempt["accounted_usd"] == before["reserved_usd"]


def test_usage_settlement_counts_cache_tokens_once_with_write_premium(
    tmp_path: Path,
) -> None:
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("10"))
    kwargs = start(ledger)
    ledger.after_call(
        context=kwargs["context"],
        parsed={
            "usage": {
                "inputTokens": 100,
                "outputTokens": 10,
                "cacheReadInputTokens": 20,
                "cacheWriteInputTokens": 30,
            }
        },
    )
    attempt = ledger.report["provider_attempts"][0]
    assert attempt["usage"]["input_tokens"] == 150
    assert Decimal(attempt["accounted_usd"]) == Decimal("0.0004565")


def test_budget_denial_stops_globally_without_creating_a_provider_attempt(
    tmp_path: Path,
) -> None:
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("0.000001"))
    with pytest.raises(BudgetFault, match="approved_spend_cap"):
        start(ledger)
    assert ledger.report["provider_attempts"] == []
    assert (
        json.loads(ledger.checkpoint.read_text())["budget_fault"]
        == "approved_spend_cap"
    )
    with pytest.raises(BudgetFault):
        start(ledger, phase="preflight")
    assert ledger.report["provider_attempts"] == []


def test_request_limit_rejects_seventh_call_before_transmission(tmp_path: Path) -> None:
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("10"))
    for _ in range(6):
        start(ledger)
    with pytest.raises(BudgetFault, match="request_or_input_envelope_exceeded"):
        start(ledger)
    assert len(ledger.report["provider_attempts"]) == 6


def test_short_context_bound_is_enforced_before_spend(tmp_path: Path) -> None:
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("10"))
    candidate = load_candidates(today=date(2026, 11, 3))[-1]
    ledger.active = (candidate, "main", "long-request", 0)
    encoded = json.dumps(
        {"inferenceConfig": {"maxTokens": 1024}, "messages": "x" * 272000}
    ).encode()
    with pytest.raises(BudgetFault, match="request_or_input_envelope_exceeded"):
        ledger.before_call(params={"body": encoded}, context={})
    assert ledger.report["provider_attempts"] == []


def test_unexpected_reported_usage_retains_cost_and_halts_all_candidates(
    tmp_path: Path,
) -> None:
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("10"))
    kwargs = start(ledger)
    with pytest.raises(BudgetFault, match="provider_usage_exceeded_reservation"):
        ledger.after_call(
            context=kwargs["context"],
            parsed={"usage": {"inputTokens": 99999, "outputTokens": 10}},
        )
    assert Decimal(ledger.report["provider_attempts"][0]["accounted_usd"]) > Decimal(
        "0.2"
    )
    with pytest.raises(BudgetFault):
        start(ledger)


def test_resume_rejects_other_experiments_and_freezes_and_preserves_unknown_spend(
    tmp_path: Path,
) -> None:
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("10"))
    start(ledger)
    value = ledger.report
    model = value["models"][KEYS[0]]
    case = model["scenarios"][0]
    case["status"] = "running"
    case["turns"][0]["status"] = "in_flight"
    spend = value["provider_attempts"][0]["accounted_usd"]
    validate_resume(value, {}, Decimal("10.00"))
    mark_interrupted(value)
    assert case["status"] == "failed"
    assert [t["status"] for t in case["turns"]] == ["failed", "not_executed"]
    assert value["provider_attempts"][0]["status"] == "usage_unknown"
    assert value["provider_attempts"][0]["accounted_usd"] == spend
    with pytest.raises(ValueError, match="source freeze"):
        validate_resume(value, {"changed": True}, Decimal("10"))
    value["benchmark"] = "historical-issue-40"
    with pytest.raises(ValueError, match="experiment"):
        validate_resume(value, {}, Decimal("10"))


def test_failed_http_capture_keeps_turn_and_cost_without_reusing_session(
    tmp_path: Path,
) -> None:
    async def run() -> dict[str, Any]:
        value = report()
        ledger = Ledger(value, tmp_path / "checkpoint.json", Decimal("10"))
        recorder = cast(
            RecordingAgent, SimpleNamespace(evidence={"old": "must be cleared"})
        )
        candidate = load_candidates(today=date(2026, 11, 3))[0]
        scenario = {"id": "transport-case", "turns": [{"message": "Olá"}]}
        turn: dict[str, Any] = {"status": "not_executed"}

        def respond(request: httpx.Request) -> httpx.Response:
            assert "session_id" not in json.loads(request.content)
            return httpx.Response(503, json={"detail": "provider unavailable"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(respond), base_url="http://test"
        ) as client:
            session = await run_turn(
                client, recorder, ledger, candidate, "main", scenario, 0, turn, None
            )
        assert session is None
        return turn

    turn = asyncio.run(run())
    assert turn["status"] == "failed" and turn["http_status"] == 503
    assert turn["model_trace"] == {}
    assert "end_to_end_latency_seconds" in turn


def completed_capture() -> dict[str, Any]:
    value = report()
    value["estimated_spend_usd"] = "0"
    for model in value["models"].values():
        model["status"] = "ready"
        for case in model["scenarios"]:
            case["status"] = "completed"
            for turn in case["turns"]:
                turn.update(status="completed", end_to_end_latency_seconds=1)
    return value


def human(verdict: str = "pass", reviewer: str = "human A") -> dict[str, Any]:
    return {
        "reviewer_type": "human",
        "reviewer": reviewer,
        "verdict": verdict,
        "critical_errors": [],
        "unsupported_claims": [],
        "missing_reads": 0,
        "incorrect_arguments": 0,
        "redundant_calls": 0,
        "evidence": "turn 1, policy section 4.1",
    }


def test_blinded_review_has_no_model_identifiers_or_fabricated_verdicts(
    tmp_path: Path,
) -> None:
    value = completed_capture()
    case = value["models"][KEYS[0]]["scenarios"][0]
    case["turns"][0]["model_trace"] = {
        "messages": [
            {
                "model_name": "amazon.nova-micro-v1:0",
                "parts": [{"content": "Evidence from amazon.nova-micro-v1:0"}],
            }
        ]
    }
    prepare_review(value, tmp_path)
    worksheet = (tmp_path / "review-worksheet.json").read_text()
    assert "amazon.nova-micro-v1:0" not in worksheet and "model_name" not in worksheet
    review = json.loads((tmp_path / "review.json").read_text())
    aliases = json.loads((tmp_path / "review-aliases.json").read_text())
    assert len(review["rows"]) == 160 and all(
        row["primary"] is None for row in review["rows"]
    )
    assert aggregate(value, review, aliases)["selection"] == "pending_human_review"
    with pytest.raises(FileExistsError):
        write_json(tmp_path / "review.json", {}, exclusive=True)


def test_selection_requires_independent_second_review_and_preserves_incumbent_tie(
    tmp_path: Path,
) -> None:
    value = completed_capture()
    prepare_review(value, tmp_path)
    review = json.loads((tmp_path / "review.json").read_text())
    aliases = json.loads((tmp_path / "review-aliases.json").read_text())
    for row in review["rows"]:
        row["primary"] = human()
    assert aggregate(value, review, aliases)["selection"] == "gpt6_luna"
    row = review["rows"][0]
    row["primary"] = human("partial")
    assert aggregate(value, review, aliases)["selection"] == "pending_human_review"
    row["second"] = human("partial")  # Same reviewer is not an independent assessment.
    assert aggregate(value, review, aliases)["selection"] == "pending_human_review"
    row["second"] = human("partial", "human B")
    assert aggregate(value, review, aliases)["status"] == "review_complete"
    row["second"] = human("fail", "human B")
    assert aggregate(value, review, aliases)["selection"] == "pending_human_review"
    row["resolution"] = human("partial", "human A")
    assert aggregate(value, review, aliases)["status"] == "review_complete"


def test_no_eligible_winner_with_critical_errors_and_no_semantic_verdict_for_failed_case(
    tmp_path: Path,
) -> None:
    value = completed_capture()
    prepare_review(value, tmp_path)
    review = json.loads((tmp_path / "review.json").read_text())
    aliases = json.loads((tmp_path / "review-aliases.json").read_text())
    for row in review["rows"]:
        primary = human("fail")
        primary["critical_errors"] = ["invented price: turn 1 vs current tool result"]
        row["primary"] = primary
        row["second"] = {**copy.deepcopy(primary), "reviewer": "human B"}
    case = value["models"][KEYS[0]]["scenarios"][0]
    case["status"] = "failed"
    case["turns"][1]["status"] = "not_executed"
    result = aggregate(value, review, aliases)
    assert result["selection"] == "no eligible winner"
    first = result["models"][0]
    assert first["verdicts"]["fail"] == 15
    assert first["http_attempted"] == 25 and first["http_planned"] == 26
    assert first["usd_per_pass"] is None
    assert result["matrix"][case["scenario_id"]][KEYS[0]] == "failed"


@pytest.mark.parametrize("key", ["nova_micro", "gpt6_luna"])
def test_serialized_converse_tool_roundtrip_is_guarded_without_network(
    key: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operational_database: Path,
) -> None:
    """Use real SDK serialization/events and local tools; stub only network I/O."""
    root = Path(__file__).resolve().parents[1]
    catalog = tmp_path / "catalog.sqlite3"
    import_catalog(
        root / "data/products.csv",
        root / "data/categories.csv",
        root / "data/promotions.csv",
        catalog,
    )
    monkeypatch.setattr(paths, "CATALOG_DATABASE_PATH", catalog)
    monkeypatch.setattr(paths, "OPERATIONS_DATABASE_PATH", operational_database)
    sdk = boto3.client(
        "bedrock-runtime",
        region_name="us-east-1",
        aws_access_key_id="offline-test",
        aws_secret_access_key="offline-test",
    )
    calls: list[dict[str, Any]] = []

    def respond(operation: Any, request: Any) -> tuple[Any, Any]:
        sent = json.loads(request["body"])
        calls.append(sent)
        content = (
            [
                {
                    "toolUse": {
                        "toolUseId": "catalog-call",
                        "name": "find_product_by_name",
                        "input": {
                            "product_name": "Yamaha C40",
                            "payment_method": "standard",
                        },
                    }
                }
            ]
            if len(calls) == 1
            else [{"text": "Consulta concluída."}]
        )
        return AWSResponse("https://offline.test", 200, {}, None), {
            "output": {"message": {"role": "assistant", "content": content}},
            "stopReason": "tool_use" if len(calls) == 1 else "end_turn",
            "usage": {"inputTokens": 100, "outputTokens": 10},
            "metrics": {"latencyMs": 1},
        }

    monkeypatch.setattr(sdk._endpoint, "make_request", respond)
    monkeypatch.setattr(
        "scripts.final_model_comparison.boto3.Session",
        lambda **kwargs: SimpleNamespace(client=lambda *a, **kw: sdk),
    )
    # Provider I/O is fully replaced above; the real SDK adapter must run in this test.
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", True)
    candidate = next(
        c for c in load_candidates(today=date(2026, 11, 3)) if c.key == key
    )
    ledger = Ledger(report(), tmp_path / "checkpoint.json", Decimal("10"))

    async def run() -> dict[str, Any]:
        client, recorder = client_for(candidate, ledger, LocalPolicySearch(), tmp_path)
        turn: dict[str, Any] = {}
        async with client:
            await run_turn(
                client,
                recorder,
                ledger,
                candidate,
                "preflight",
                {"id": "preflight", "turns": [{"message": "Consulte o Yamaha C40."}]},
                0,
                turn,
                None,
            )
        return turn

    turn = asyncio.run(run())
    assert turn["status"] == "completed" and preflight_success(turn)
    assert len(calls) == len(ledger.report["provider_attempts"]) == 2
    assert all(a["usage"] is not None for a in ledger.report["provider_attempts"])
    assert all(
        a["serialized_settings"]["inferenceConfig"]["maxTokens"] == 1024
        for a in ledger.report["provider_attempts"]
    )
    assert "offline-test" not in json.dumps(ledger.report)


def test_review_rejects_llm_judges_and_pass_with_critical_error(tmp_path: Path) -> None:
    value = completed_capture()
    prepare_review(value, tmp_path)
    review = json.loads((tmp_path / "review.json").read_text())
    aliases = json.loads((tmp_path / "review-aliases.json").read_text())
    row = review["rows"][0]
    row["primary"] = {**human(), "reviewer_type": "llm"}
    with pytest.raises(ValueError, match="human"):
        aggregate(value, review, aliases)
    row["primary"] = {**human(), "critical_errors": ["privacy leak"]}
    with pytest.raises(ValueError, match="requires Fail"):
        aggregate(value, review, aliases)
