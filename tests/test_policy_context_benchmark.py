"""Offline guards for the bounded issue #78 benchmark runner."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from scripts.benchmark_support import Candidate
from scripts.compare_policy_context import (
    MODEL_ID,
    BudgetStop,
    Ledger,
    embedded_instructions,
    load_scenarios,
    load_luna_candidate,
    input_paths,
    operational_metrics,
)


def _luna_candidate() -> Candidate:
    return Candidate(
        key="gpt6_luna",
        model_id="openai.gpt-6-luna",
        inference_endpoint="bedrock-runtime",
        inference_model_id=MODEL_ID,
        inference_api="converse",
        context_window_tokens=1_050_000,
        input_usd_per_million=Decimal("0.11"),
        output_usd_per_million=Decimal("0.55"),
        tool_use_status="verified",
        long_context_threshold_tokens=272_000,
        long_context_input_usd_per_million=Decimal("0.22"),
        long_context_output_usd_per_million=Decimal("0.825"),
        cache_write_usd_per_million=Decimal("0.1375"),
        long_context_cache_write_usd_per_million=Decimal("0.275"),
    )


def test_embedded_policy_arm_contains_corpus_without_rag_tool() -> None:
    instructions = embedded_instructions('{"source":"fixture"}')

    assert "search_store_policies" not in instructions
    assert "Corpus de políticas revisado" in instructions
    assert '{"source":"fixture"}' in instructions
    assert "Contato geral não é automaticamente SAC" in instructions


def test_issue_78_fixture_has_twelve_paired_conversations_and_eighteen_turns() -> None:
    scenarios = load_scenarios()

    assert len(scenarios) == 12
    assert sum(len(scenario["turns"]) for scenario in scenarios) == 18
    assert [scenario["id"] for scenario in scenarios] == [
        f"C{index:02}" for index in range(1, 13)
    ]
    assert scenarios[-1]["turns"][0]["unanswerable"] is True


def test_budget_guard_rejects_before_creating_a_provider_attempt(
    tmp_path: Path,
) -> None:
    candidate = _luna_candidate()

    class Verifier:
        def verify(self) -> None:
            return None

    report: dict[str, Any] = {"provider_attempts": []}
    ledger = Ledger(
        report,
        tmp_path / "checkpoint.json",
        Decimal("0.000001"),
        candidate,
        Verifier(),  # type: ignore[arg-type]
    )
    ledger.active = {
        "arm": "rag",
        "phase": "main",
        "scenario_id": "C01",
        "turn_index": 0,
    }
    params = {
        "url_path": f"/model/{MODEL_ID}/converse",
        "body": json.dumps({"inferenceConfig": {"maxTokens": 1024}}).encode(),
    }

    with pytest.raises(BudgetStop, match="approved_spend_cap"):
        ledger.before_call(params=params, context={})

    assert report["provider_attempts"] == []
    assert report["budget_fault"] == "approved_spend_cap"
    assert (tmp_path / "checkpoint.json").is_file()


def test_provider_accounting_includes_cache_tokens_in_input_and_cost(
    tmp_path: Path,
) -> None:
    candidate = _luna_candidate()

    class Verifier:
        def verify(self) -> None:
            return None

    attempt = {
        "arm": "rag",
        "phase": "main",
        "scenario_id": "C01",
        "turn_index": 0,
        "status": "in_flight",
        "input_upper_bound": 200,
        "reserved_usd": "0.001",
        "accounted_usd": "0.001",
        "usage": None,
    }
    report: dict[str, Any] = {"provider_attempts": [attempt]}
    ledger = Ledger(
        report,
        tmp_path / "checkpoint.json",
        Decimal("1.00"),
        candidate,
        Verifier(),  # type: ignore[arg-type]
    )

    ledger.after_call(
        context={"issue_78_attempt_index": 0},
        parsed={
            "usage": {
                "inputTokens": 10,
                "cacheReadInputTokens": 100,
                "cacheWriteInputTokens": 50,
                "outputTokens": 20,
            }
        },
    )

    assert isinstance(attempt["usage"], dict)
    assert attempt["usage"]["total_input_tokens"] == 160
    assert attempt["accounted_usd"] == "0.000020075"


def test_provider_usage_stops_when_cached_tokens_exceed_input_bound(
    tmp_path: Path,
) -> None:
    class Verifier:
        def verify(self) -> None:
            return None

    attempt = {
        "arm": "rag",
        "phase": "main",
        "scenario_id": "C01",
        "turn_index": 0,
        "status": "in_flight",
        "input_upper_bound": 159,
        "max_output_tokens": 1024,
        "reserved_usd": "0.001",
        "accounted_usd": "0.001",
        "usage": None,
    }
    report: dict[str, Any] = {"provider_attempts": [attempt]}
    ledger = Ledger(
        report,
        tmp_path / "checkpoint.json",
        Decimal("1.00"),
        _luna_candidate(),
        Verifier(),  # type: ignore[arg-type]
    )

    with pytest.raises(BudgetStop, match="provider_usage_exceeded_reservation"):
        ledger.after_call(
            context={"issue_78_attempt_index": 0},
            parsed={
                "usage": {
                    "inputTokens": 10,
                    "cacheReadInputTokens": 100,
                    "cacheWriteInputTokens": 50,
                    "outputTokens": 20,
                }
            },
        )

    assert isinstance(attempt["usage"], dict)
    assert attempt["usage"]["total_input_tokens"] == 160
    assert report["budget_fault"] == "provider_usage_exceeded_reservation"


def test_tool_compliance_does_not_require_rag_policy_tool_in_embedded_arm() -> None:
    scenarios = [
        {
            "id": "C01",
            "turns": [
                {
                    "message": "Confira o pedido e a regra de devolução.",
                    "required_tools": ["get_my_order", "search_store_policies"],
                }
            ],
        }
    ]
    report: dict[str, Any] = {
        "provider_attempts": [],
        "conversations": {
            "C01": {
                arm: {
                    "status": "completed",
                    "turns": [
                        {
                            "status": "completed",
                            "latency_seconds": 1.0,
                            "tool_calls": [{"name": "get_my_order"}],
                            "policy_search_events": [],
                        }
                    ],
                }
                for arm in ("rag", "embedded")
            }
        },
    }

    metrics = operational_metrics(report, scenarios, _luna_candidate())

    assert metrics["by_arm"]["rag"]["missing_required_tool_turns"] == [
        {"scenario_id": "C01", "turn_index": 0, "tools": ["search_store_policies"]}
    ]
    assert metrics["by_arm"]["embedded"]["missing_required_tool_turns"] == []


def test_current_comparison_inputs_exclude_retired_benchmarks() -> None:
    names = [path.as_posix() for path in input_paths()]
    assert not any("docs/examples/" in path for path in names)
    assert not any("docs/benchmarks/expansion/" in path for path in names)
    assert any(path.endswith("/scripts/benchmark_pricing.json") for path in names)
    assert any(path.endswith("/scripts/benchmark_support.py") for path in names)


def test_luna_candidate_loads_standalone_verified_prices() -> None:
    candidate = load_luna_candidate(today=date(2026, 11, 3))
    assert candidate.inference_model_id == MODEL_ID
    assert candidate.input_usd_per_million == Decimal("0.11")
    assert candidate.output_usd_per_million == Decimal("0.55")


def test_luna_candidate_rejects_stale_and_unverified_prices(tmp_path: Path) -> None:
    from scripts.compare_policy_context import PRICING_FILE

    document = json.loads(PRICING_FILE.read_text(encoding="utf-8"))
    fixture = tmp_path / "pricing.json"
    fixture.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="Reverify Luna"):
        load_luna_candidate(today=date(2026, 11, 4), pricing_file=fixture)

    document["model"]["inference_model_id"] = "wrong-model"
    fixture.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Runtime Converse"):
        load_luna_candidate(today=date(2026, 11, 3), pricing_file=fixture)
