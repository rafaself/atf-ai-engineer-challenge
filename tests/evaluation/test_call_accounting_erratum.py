"""Errata distinguish provider attempts and preserve historical evidence."""

import json
from pathlib import Path

from scripts.review_call_accounting import review_capture


def test_erratum_excludes_synthetic_history_without_rewriting_evidence(
    tmp_path: Path,
) -> None:
    path = tmp_path / "capture.json"
    raw = json.dumps(
        {
            "model_runs": [
                {
                    "model_id": "test-model",
                    "model_calls": 2,
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "estimated_cost_usd": "0.001",
                    "scenarios": [
                        {
                            "turns": [
                                {
                                    "status": "completed",
                                    "provider_request_counter": 1,
                                    "model_trace": {
                                        "messages": [
                                            {
                                                "kind": "response",
                                                "usage": {
                                                    "input_tokens": 0,
                                                    "output_tokens": 0,
                                                },
                                            },
                                            {
                                                "kind": "response",
                                                "model_name": "test-model",
                                                "finish_reason": "stop",
                                                "usage": {
                                                    "input_tokens": 10,
                                                    "output_tokens": 5,
                                                },
                                            },
                                        ]
                                    },
                                }
                            ]
                        }
                    ],
                }
            ]
        }
    ).encode()
    path.write_bytes(raw)
    model = review_capture(path)["models"][0]
    assert model["reported_model_calls"] == 2
    assert model["observed_provider_attempts"] == 1
    assert model["current_response_records"] == 1
    assert model["synthetic_history_response_records"] == 1
    assert model["token_totals_reconcile"] is True
    assert model["recorded_estimated_cost_usd"] == "0.001"
    assert path.read_bytes() == raw
