import asyncio
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from emporio_music_backend import paths
from emporio_music_backend.agent.settings import AgentSettings
from scripts.compare_models import (
    Candidate,
    RequestCounter,
    _check_local_retrieval_readiness,
    _copy_policy_inputs,
    _execution_failure_category,
    _model_executor,
    _provider_unavailable,
    _scenario_was_attempted,
    _sha256,
    _summary,
    _tree_sha256,
    estimate_usage_cost,
    load_project_aws_environment,
    load_scenarios,
    load_verified_candidates,
    run_comparison,
    turn_reservation_usd,
    validate_endpoint_tool_manifest,
)


def test_frozen_comparison_contains_nine_scenarios_and_sixteen_turns() -> None:
    scenarios = load_scenarios()

    assert len(scenarios) == 9
    assert sum(len(scenario["turns"]) for scenario in scenarios) == 16


def test_local_retrieval_readiness_loads_the_existing_index_and_cached_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, str]] = []

    class ReadySearch:
        def __init__(self, *, data_directory: Path) -> None:
            self.data_directory = data_directory

        def search(self, query: str) -> dict[str, object]:
            calls.append((self.data_directory, query))
            return {"status": "evidence_found", "records": [{"section": "2"}]}

    monkeypatch.setattr("scripts.compare_models.LocalPolicySearch", ReadySearch)

    result = _check_local_retrieval_readiness()

    assert result["status"] == "ready"
    assert result["embedding_model"] == "intfloat/multilingual-e5-base"
    assert result["index_collection"] == "policy-e5"
    assert calls == [(paths.DATA_DIRECTORY, "horário de funcionamento da loja")]


def test_local_retrieval_readiness_reports_missing_local_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_dependency = ModuleNotFoundError(
        "missing local model package", name="sentence_transformers"
    )

    class MissingDependencySearch:
        def __init__(self, *, data_directory: Path) -> None:
            self.data_directory = data_directory

        def search(self, _query: str) -> dict[str, object]:
            raise RuntimeError("local retrieval failed") from missing_dependency

    monkeypatch.setattr(
        "scripts.compare_models.LocalPolicySearch", MissingDependencySearch
    )

    result = _check_local_retrieval_readiness()

    assert result["status"] == "blocked"
    assert result["failure_type"] == "RuntimeError"
    assert result["cause_type"] == "ModuleNotFoundError"
    assert result["missing_module"] == "sentence_transformers"


def test_scenario_tool_expectations_match_the_registered_agent_tools() -> None:
    scenarios = load_scenarios()
    registered_tools = {
        "search_available_products",
        "get_product_details",
        "list_my_orders",
        "get_my_order",
        "search_store_policies",
        "find_product_alternatives",
    }
    required_tools = {
        tool
        for scenario in scenarios
        for tool in scenario["expected"]["required_tools"]
    }

    assert required_tools <= registered_tools
    no_match = next(s for s in scenarios if s["id"] == "no-match")
    assert no_match["expected"]["required_tools"] == ["get_product_details"]


def test_current_benchmark_fixture_uses_approved_freight_and_updated_expectations() -> (
    None
):
    scenarios = load_scenarios(
        paths.PROJECT_ROOT / "docs/examples/model-comparison/scenarios-current-v3.json"
    )

    freight = next(s for s in scenarios if s["id"] == "freight-exact-threshold")
    assert any("R$ 500.00 or more" in fact for fact in freight["expected"]["facts"])

    holidays = next(
        s for s in scenarios if s["id"] == "policy-hours-context-topic-change"
    )
    assert any("do not assert either" in fact for fact in holidays["expected"]["facts"])
    assert any(
        "deterministic snapshot notice" in fact
        for fact in holidays["expected"]["facts"]
    )


def test_turn_reservation_covers_each_allowed_request_at_context_ceiling() -> None:
    candidate = Candidate(
        key="test",
        model_id="test.model",
        inference_endpoint="bedrock-runtime",
        inference_model_id="test.model",
        inference_api="converse",
        context_window_tokens=1_000,
        input_usd_per_million=Decimal("0.10"),
        output_usd_per_million=Decimal("0.20"),
        tool_use_status="verified",
    )

    assert turn_reservation_usd(
        candidate, max_requests=5, max_output_tokens=100
    ) == Decimal("0.0006")


def test_usage_estimate_reserves_missing_usage_at_full_request_ceiling() -> None:
    candidate = Candidate(
        key="test",
        model_id="test.model",
        inference_endpoint="bedrock-runtime",
        inference_model_id="test.model",
        inference_api="converse",
        context_window_tokens=1_000,
        input_usd_per_million=Decimal("0.10"),
        output_usd_per_million=Decimal("0.20"),
        tool_use_status="verified",
    )

    cost, usage = estimate_usage_cost(
        candidate,
        {"usage": {"responses": [{"input_tokens": 100, "output_tokens": 10}]}},
        observed_requests=2,
        max_output_tokens=100,
    )

    assert cost == Decimal("0.000132")
    assert usage["requests_with_usage"] == 1
    assert usage["requests_with_missing_usage"] == 1


def _manifest_review_date(key: str = "checked_at_utc") -> date:
    manifest = json.loads(
        (paths.PROJECT_ROOT / "docs/examples/model-comparison/pricing.json").read_text()
    )
    return date.fromisoformat(manifest[key][:10])


def test_verified_rates_and_routes_load_from_the_current_manifest() -> None:
    candidates = load_verified_candidates(today=_manifest_review_date())

    assert [candidate.key for candidate in candidates] == [
        "qwen3_32b",
        "nova_micro",
        "nova_lite",
        "gpt_oss_20b",
        "gpt_oss_120b",
    ]
    assert candidates[0].inference_endpoint == "bedrock-runtime"
    assert candidates[0].inference_model_id == "qwen.qwen3-32b-v1:0"
    assert candidates[0].inference_api == "converse"
    assert candidates[0].input_usd_per_million == Decimal("0.15")
    assert candidates[0].output_usd_per_million == Decimal("0.6")


def test_verified_candidates_can_select_only_qwen_and_nova_lite() -> None:
    candidates = load_verified_candidates(
        today=_manifest_review_date(), model_keys=("qwen3_32b", "nova_lite")
    )

    assert [candidate.key for candidate in candidates] == [
        "qwen3_32b",
        "nova_lite",
    ]


def test_project_aws_environment_load_is_silent_and_limited_to_aws_keys(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    expected_keys = {
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
    }
    calls: list[tuple[Path, bool]] = []
    environment = SimpleNamespace(environ={})

    def fake_dotenv_values(path: Path, *, verbose: bool) -> dict[str, str]:
        calls.append((path, verbose))
        return {name: "test-only-secret" for name in expected_keys} | {
            "UNRELATED_SETTING": "not loaded"
        }

    monkeypatch.setattr("scripts.compare_models.os", environment)
    monkeypatch.setattr("scripts.compare_models.dotenv_values", fake_dotenv_values)

    load_project_aws_environment()

    assert calls == [(paths.PROJECT_ROOT / ".env", False)]
    assert set(environment.environ) == expected_keys
    assert capsys.readouterr().out == ""


def test_endpoint_tool_verification_expires_after_the_review_date() -> None:
    validate_endpoint_tool_manifest(
        today=_manifest_review_date("endpoint_tool_checked_at_utc")
    )

    with pytest.raises(ValueError, match="endpoint tool compatibility"):
        validate_endpoint_tool_manifest(
            today=_manifest_review_date("endpoint_tool_checked_at_utc")
            + timedelta(days=1)
        )


def test_verified_candidates_use_model_card_endpoint_and_api_combinations() -> None:
    manifest = json.loads(
        (paths.PROJECT_ROOT / "docs/examples/model-comparison/pricing.json").read_text(
            encoding="utf-8"
        )
    )
    routes = {
        item["key"]: (item["inference_endpoint"], item["inference_api"])
        for item in manifest["models"]
    }

    assert routes == {
        "nova_micro": ("bedrock-runtime", "converse"),
        "nova_lite": ("bedrock-runtime", "converse"),
        "qwen3_32b": ("bedrock-runtime", "converse"),
        "gpt_oss_20b": ("bedrock-runtime", "converse"),
        "gpt_oss_120b": ("bedrock-runtime", "converse"),
    }


def test_model_executor_rejects_non_runtime_route_before_provider_setup(
    tmp_path: Path,
) -> None:
    candidate = Candidate(
        key="unsupported",
        model_id="unsupported.model",
        inference_endpoint="bedrock-mantle",
        inference_model_id="unsupported.model",
        inference_api="chat-completions",
        context_window_tokens=1_000,
        input_usd_per_million=Decimal("0.10"),
        output_usd_per_million=Decimal("0.20"),
        tool_use_status="verified",
    )

    with pytest.raises(ValueError, match="Bedrock Runtime Converse"):
        _model_executor(candidate, AgentSettings(), RequestCounter(), tmp_path)


def test_only_provider_503_stops_independent_scenarios() -> None:
    local_policy_failure = {
        "failure": {
            "causes": ["PolicyRetrievalError", "ModuleNotFoundError"],
            "aws_error_code": None,
        }
    }
    provider_failure = {
        "failure": {
            "causes": ["ProviderUnavailableError", "ServiceUnavailableException"],
            "aws_error_code": "ServiceUnavailableException",
        }
    }

    assert not _provider_unavailable(503, local_policy_failure)
    assert _provider_unavailable(503, provider_failure)
    assert not _provider_unavailable(500, provider_failure)


def test_execution_failures_keep_provider_and_local_causes_separate() -> None:
    local_failure = {
        "failure": {
            "causes": ["PolicyRetrievalError", "ModuleNotFoundError"],
            "aws_error_code": None,
        }
    }
    provider_failure = {
        "failure": {
            "causes": ["ProviderUnavailableError", "ServiceUnavailableException"],
            "aws_error_code": "ServiceUnavailableException",
        }
    }

    assert (
        _execution_failure_category(503, local_failure, None) == "local_infrastructure"
    )
    assert _execution_failure_category(503, provider_failure, None) == "provider_or_sdk"
    assert _execution_failure_category(None, {}, "ConnectError") == "transport"


def test_resume_skips_any_scenario_with_a_paid_or_failed_turn() -> None:
    assert _scenario_was_attempted({"attempted_turns": 1, "turns": []})
    assert _scenario_was_attempted(
        {"attempted_turns": 0, "turns": [{"status": "failed"}]}
    )
    assert not _scenario_was_attempted(
        {"attempted_turns": 0, "turns": [{"status": "not_executed"}]}
    )


def test_policy_search_inputs_are_copied_without_changing_the_frozen_index(
    tmp_path: Path,
) -> None:
    source_index = paths.DATA_DIRECTORY / "policy-indexes"
    source_pdf = paths.DATA_DIRECTORY / "store_policies.pdf"
    index_before = _tree_sha256(source_index)
    pdf_before = _sha256(source_pdf)

    copied = _copy_policy_inputs(tmp_path / "policy-data")

    assert _tree_sha256(copied / "policy-indexes") == index_before
    assert _sha256(copied / "store_policies.pdf") == pdf_before
    assert _tree_sha256(source_index) == index_before
    assert _sha256(source_pdf) == pdf_before


def test_paid_runner_rejects_budget_above_approved_cap_before_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "capture.json"

    with pytest.raises(ValueError, match=r"US\$1.00"):
        asyncio.run(run_comparison(output=output, max_cost_usd=Decimal("1.01")))

    assert not output.exists()


def test_live_runner_uses_baseline_probe_when_availability_permission_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup_attempts: list[str] = []

    def blocked_provider_preflight(
        *_args: object, **_kwargs: object
    ) -> dict[str, object]:
        return {
            "status": "blocked",
            "failure_type": "AccessDeniedException",
            "paid_calls": 0,
            "models": [],
        }

    def fail_provider_setup(
        candidate: Candidate,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        setup_attempts.append(candidate.key)
        raise RuntimeError("controlled setup failure")

    monkeypatch.setattr(
        "scripts.compare_models.probe_model_access", blocked_provider_preflight
    )
    monkeypatch.setattr("scripts.compare_models._model_executor", fail_provider_setup)
    monkeypatch.setattr(
        "scripts.compare_models._check_local_retrieval_readiness",
        lambda: {"status": "ready"},
        raising=False,
    )
    report = asyncio.run(
        run_comparison(output=tmp_path / "capture.json", max_cost_usd=Decimal("1.00"))
    )

    assert report["status"] == "stopped_provider_failure"
    assert report["pricing_verification"] == "verified_today"
    assert (
        report["account_preflight_resolution"]
        == "availability_api_denied_use_approved_baseline_probe"
    )
    assert setup_attempts == ["qwen3_32b"]
    assert report["paid_calls"] == 0
    assert report["model_runs"][0]["status"] == "excluded_provider_setup_failure"
    assert [item["status"] for item in report["model_runs"][1:]] == [
        "not_executed_provider_failure",
        "not_executed_provider_failure",
        "not_executed_provider_failure",
        "not_executed_provider_failure",
    ]


def test_live_runner_stops_before_provider_access_when_retrieval_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider_probes: list[str] = []
    model_setups: list[str] = []

    def retrieval_not_ready() -> dict[str, object]:
        return {
            "status": "blocked",
            "failure_type": "PolicyRetrievalError",
            "cause_type": "ModuleNotFoundError",
        }

    def record_provider_probe(*_args: object, **_kwargs: object) -> dict[str, object]:
        provider_probes.append("called")
        return {"status": "blocked", "paid_calls": 0, "models": []}

    def record_model_setup(
        candidate: Candidate, *_args: object, **_kwargs: object
    ) -> None:
        model_setups.append(candidate.key)
        raise AssertionError("provider setup must not follow a failed readiness check")

    monkeypatch.setattr(
        "scripts.compare_models._check_local_retrieval_readiness",
        retrieval_not_ready,
        raising=False,
    )
    monkeypatch.setattr(
        "scripts.compare_models.probe_model_access", record_provider_probe
    )
    monkeypatch.setattr("scripts.compare_models._model_executor", record_model_setup)

    report = asyncio.run(
        run_comparison(output=tmp_path / "blocked.json", max_cost_usd=Decimal("1.00"))
    )

    assert report["status"] == "blocked_retrieval_readiness"
    assert report["retrieval_readiness"]["status"] == "blocked"
    assert report["paid_calls"] == 0
    assert provider_probes == []
    assert model_setups == []


def test_summary_handles_transport_errors_without_http_status() -> None:
    result = _summary(
        [
            {
                "model_id": "test.model",
                "scenarios": [
                    {
                        "attempted_turns": 1,
                        "estimated_cost_usd": "0.10",
                        "turns": [
                            {
                                "http_status": None,
                                "end_to_end_latency_seconds": 0.25,
                                "tool_calls": [{"name": "search_products"}],
                                "usage": {"requests_with_missing_usage": 1},
                            }
                        ],
                    }
                ],
            }
        ]
    )[0]

    assert result["http_errors"] == 0
    assert result["tool_calls"] == 1
    assert result["requests_with_missing_usage"] == 1
    assert result["median_end_to_end_latency_seconds"] == 0.25


def test_summary_separates_execution_failures_from_semantic_verdicts() -> None:
    result = _summary(
        [
            {
                "model_id": "test.model",
                "scenarios": [
                    {
                        "scenario_id": "complete",
                        "status": "completed",
                        "manual_review": "complete",
                        "manual_verdict": "pass",
                        "attempted_turns": 1,
                        "estimated_cost_usd": "0.10",
                        "turns": [
                            {
                                "status": "completed",
                                "http_status": 200,
                                "end_to_end_latency_seconds": 1.5,
                            }
                        ],
                    },
                    {
                        "scenario_id": "local-retrieval-error",
                        "status": "failed",
                        "manual_review": "not_evaluated",
                        "manual_verdict": None,
                        "attempted_turns": 1,
                        "estimated_cost_usd": "0.20",
                        "execution_failure": {"category": "local_infrastructure"},
                        "turns": [
                            {
                                "status": "failed",
                                "http_status": 503,
                                "end_to_end_latency_seconds": 2.5,
                            },
                            {"status": "not_executed"},
                        ],
                    },
                ],
            }
        ]
    )[0]

    assert result["scenario_verdicts"] == {"pass": 1, "partial": 0, "fail": 0}
    assert result["attempted_conversations"] == 2
    assert result["evaluated_conversations"] == 1
    assert result["reviewed_conversations"] == 1
    assert result["execution_failed_conversations"] == 1
    assert result["execution_failure_categories"] == {"local_infrastructure": 1}
    assert result["not_executed_turns"] == 1
    assert result["attempted_http_turns"] == 2
    assert result["http_errors"] == 1
    assert result["median_end_to_end_latency_seconds"] == 2.0
    assert result["maximum_end_to_end_latency_seconds"] == 2.5
    assert result["cost_per_fully_successful_conversation_usd"] == "0.30000000"
