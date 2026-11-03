"""Offline guards for the bounded issue #78 benchmark runner."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from scripts.compare_models import Candidate
from scripts.compare_policy_context import (
    MODEL_ID,
    BudgetStop,
    Ledger,
    embedded_instructions,
    load_scenarios,
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
    candidate = Candidate(
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
