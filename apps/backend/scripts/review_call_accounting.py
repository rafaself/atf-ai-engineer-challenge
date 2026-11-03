"""Read-only historical call-count review; original captures are never rewritten."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def review_capture(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    capture = json.loads(raw)
    models = []
    for model in capture.get("model_runs", []):
        turns = [
            turn
            for case in model.get("scenarios", [])
            for turn in case.get("turns", [])
            if turn.get("status") != "not_executed"
        ]
        counters_complete = bool(turns) and all(
            isinstance(turn.get("provider_request_counter"), int)
            and not turn.get("request_count_unavailable")
            for turn in turns
        )
        attempts = sum(turn.get("provider_request_counter", 0) for turn in turns)
        synthetic: list[dict[str, Any]] = []
        current: list[dict[str, Any]] = []
        for turn in turns:
            for message in turn.get("model_trace", {}).get("messages", []):
                if message.get("kind") != "response":
                    continue
                usage = message.get("usage", {})
                historical = (
                    message.get("model_name") is None
                    and message.get("finish_reason") is None
                    and not usage.get("input_tokens")
                    and not usage.get("output_tokens")
                )
                (synthetic if historical else current).append(message)
        input_tokens = sum(
            int(message.get("usage", {}).get("input_tokens", 0) or 0)
            for message in current
        )
        output_tokens = sum(
            int(message.get("usage", {}).get("output_tokens", 0) or 0)
            for message in current
        )
        models.append(
            {
                "model_id": model["model_id"],
                "reported_model_calls": model.get("model_calls"),
                "observed_provider_attempts": attempts if counters_complete else None,
                "provider_counters_complete": counters_complete,
                "current_response_records": len(current),
                "synthetic_history_response_records": len(synthetic),
                "provider_only_input_tokens": input_tokens,
                "provider_only_output_tokens": output_tokens,
                "token_totals_reconcile": input_tokens == model.get("input_tokens")
                and output_tokens == model.get("output_tokens"),
                "recorded_estimated_cost_usd": model.get("estimated_cost_usd"),
            }
        )
    return {
        "capture": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "models": models,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "explanation": "Reported model_calls could include reconstructed assistant history. Observed provider attempts cover evaluation HTTP turns only; separately recorded access/baseline probes are not added here. Zero-usage historical responses do not add token cost. Reconciliation is recorded per model, not assumed. Raw captures and semantic verdicts remain unchanged.",
        "captures": [
            review_capture(path)
            for path in sorted(args.capture_directory.glob("capture-*.json"))
        ],
    }
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
