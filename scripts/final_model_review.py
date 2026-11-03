"""Prepare human worksheets and aggregate explicitly labeled issue #82 reviews."""

from __future__ import annotations

import argparse
import json
import random
import secrets
import statistics
from decimal import Decimal
from pathlib import Path
from typing import Any

from scripts.final_model_comparison import IDENTITY, KEYS, write_json


def prepare_review(capture: dict[str, Any], directory: Path) -> None:
    """Create empty human forms; never infer semantic verdicts from model text."""
    if capture.get("benchmark") != IDENTITY:
        raise ValueError("Not an issue #82 capture")
    keys = list(KEYS)
    random.SystemRandom().shuffle(keys)
    aliases = {key: f"Candidate {index + 1:02d}" for index, key in enumerate(keys)}
    names = {
        name: aliases[key]
        for key, value in capture["models"].items()
        for name in (
            key,
            value["model"]["model_id"],
            value["model"]["inference_model_id"],
        )
    }

    def blind(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k: blind(v)
                for k, v in value.items()
                if k
                not in {
                    "model_name",
                    "provider_name",
                    "provider_url",
                    "model",
                    "model_key",
                    "model_id",
                    "inference_model_id",
                    "provider_details",
                    "serialized_settings",
                }
            }
        if isinstance(value, list):
            return [blind(v) for v in value]
        if isinstance(value, str):
            for name in sorted(names, key=len, reverse=True):
                value = value.replace(name, names[name])
        return value

    rows = []
    worksheet = []
    for key in keys:
        for case in capture["models"][key]["scenarios"]:
            row = {
                "candidate": aliases[key],
                "scenario_id": case["scenario_id"],
                "execution_status": case["status"],
                "primary": None,
                "second": None,
                "resolution": None,
            }
            rows.append(row)
            worksheet.append({"candidate": aliases[key], "evidence": blind(case)})
    seed = secrets.randbits(64)
    random.Random(seed).shuffle(rows)
    random.Random(seed).shuffle(worksheet)
    write_json(directory / "review-aliases.json", aliases, exclusive=True)
    write_json(
        directory / "review.json",
        {
            "benchmark": IDENTITY,
            "status": "pending_human_review",
            "instructions": {
                "primary": "Human reviewer, verdict pass/partial/fail, critical_errors, unsupported_claims, missing_reads, incorrect_arguments, redundant_calls, evidence and notes.",
                "second": "Independent human assessment with the same fields and a different reviewer; required for any Partial/Fail/critical finding by either reviewer.",
                "resolution": "For disagreements: resolved assessment plus exact evidence; all original judgments remain preserved.",
                "blinding": "Give reviewers review-worksheet.json, not the capture or alias map. Freeze primary judgments before revealing aliases.",
                "tool_counts": "Nonnegative integer counts; critical_errors and unsupported_claims are evidence-linked lists.",
            },
            "rows": rows,
        },
        exclusive=True,
    )
    write_json(
        directory / "review-worksheet.json",
        {"benchmark": IDENTITY, "conversations": worksheet},
        exclusive=True,
    )


def assessment(value: Any, *, reviewer_type: str = "human") -> dict[str, Any] | None:
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or value.get("reviewer_type") != reviewer_type
        or not str(value.get("reviewer", "")).strip()
    ):
        raise ValueError(
            f"Assessments must identify an actual {reviewer_type} reviewer"
        )
    if value.get("verdict") not in {"pass", "partial", "fail"}:
        raise ValueError("Review verdict must be pass, partial or fail")
    for field in ("critical_errors", "unsupported_claims"):
        if not isinstance(value.get(field), list):
            raise ValueError(f"Missing review list: {field}")
    for field in ("missing_reads", "incorrect_arguments", "redundant_calls"):
        if type(value.get(field)) is not int or value[field] < 0:
            raise ValueError(f"Invalid tool diagnostic count: {field}")
    if value["critical_errors"] and value["verdict"] != "fail":
        raise ValueError("Any critical error requires Fail")
    if value["unsupported_claims"] and value["verdict"] == "pass":
        raise ValueError("Unsupported material claims cannot receive Pass")
    if value["verdict"] != "pass" and not value.get("evidence"):
        raise ValueError("Partial/Fail requires exact evidence")
    return value


def reviewed_value(
    row: dict[str, Any], *, ai_authorized: bool = False
) -> dict[str, Any] | None:
    primary = assessment(
        row.get("primary"), reviewer_type="ai" if ai_authorized else "human"
    )
    if ai_authorized:
        return primary  # Owner waived human review; never fabricate a second reviewer.
    second = assessment(row.get("second"))
    if primary is None:
        return None
    needs_second = any(a and a["verdict"] != "pass" for a in (primary, second))
    if needs_second and (second is None or primary["reviewer"] == second["reviewer"]):
        return None
    compared = (
        "verdict",
        "critical_errors",
        "unsupported_claims",
        "missing_reads",
        "incorrect_arguments",
        "redundant_calls",
    )
    if second is not None and any(primary[k] != second[k] for k in compared):
        resolved = assessment(row.get("resolution"))
        if resolved is None or not resolved.get("evidence"):
            return None
        return resolved
    return primary


def aggregate(
    capture: dict[str, Any],
    review: dict[str, Any],
    aliases: dict[str, str],
    *,
    allow_ai: bool = False,
) -> dict[str, Any]:
    if capture.get("benchmark") != IDENTITY or review.get("benchmark") != IDENTITY:
        raise ValueError("Capture and review must belong to this independent benchmark")
    method = review.get("review_method", "human")
    if method not in {"human", "ai_user_authorized"}:
        raise ValueError("Unknown review method")
    ai_authorized = method == "ai_user_authorized"
    if ai_authorized and (not allow_ai or not review.get("owner_authorization")):
        raise ValueError(
            "AI assessment requires explicit owner authorization and --allow-ai-review"
        )
    pending_label = "pending_ai_review" if ai_authorized else "pending_human_review"
    if set(aliases) != set(KEYS) or len(set(aliases.values())) != 10:
        raise ValueError("Alias map must identify all ten candidates uniquely")
    expected = {
        (aliases[key], case["scenario_id"])
        for key in KEYS
        for case in capture["models"][key]["scenarios"]
    }
    rows = {(row["candidate"], row["scenario_id"]): row for row in review["rows"]}
    if len(rows) != len(review["rows"]) or set(rows) != expected:
        raise ValueError("Missing, duplicate or unknown review rows")
    summaries = []
    matrix: dict[str, dict[str, str]] = {}
    pending = False
    for key in KEYS:
        model = capture["models"][key]
        cases = model["scenarios"]
        turns = [turn for case in cases for turn in case["turns"]]
        attempted = [turn for turn in turns if turn["status"] != "not_executed"]
        successful = sum(turn["status"] == "completed" for turn in turns)
        latencies = [
            turn["end_to_end_latency_seconds"]
            for turn in attempted
            if "end_to_end_latency_seconds" in turn
        ]
        main_attempts = [
            a
            for a in capture["provider_attempts"]
            if a["model_key"] == key and a["phase"] == "main"
        ]
        cost = sum((Decimal(a["accounted_usd"]) for a in main_attempts), Decimal(0))
        preflight_cost = sum(
            (
                Decimal(a["accounted_usd"])
                for a in capture["provider_attempts"]
                if a["model_key"] == key and a["phase"] == "preflight"
            ),
            Decimal(0),
        )
        counts = {name: 0 for name in ("pass", "partial", "fail")}
        diagnostics = {
            name: 0
            for name in (
                "critical_errors",
                "unsupported_claims",
                "missing_reads",
                "incorrect_arguments",
                "redundant_calls",
            )
        }
        reviewed = 0
        for case in cases:
            verdict = case["status"]
            if verdict == "completed":
                result = reviewed_value(
                    rows[(aliases[key], case["scenario_id"])],
                    ai_authorized=ai_authorized,
                )
                if result is None:
                    pending = True
                    verdict = pending_label
                else:
                    reviewed += 1
                    verdict = result["verdict"]
                    counts[verdict] += 1
                    for name in diagnostics:
                        diagnostics[name] += (
                            len(result[name])
                            if isinstance(result[name], list)
                            else result[name]
                        )
            matrix.setdefault(case["scenario_id"], {})[key] = verdict
        known_usage = [a["usage"] for a in main_attempts if a.get("usage") is not None]
        input_tokens = sum(u["input_tokens"] for u in known_usage)
        output_tokens = sum(u["output_tokens"] for u in known_usage)
        eligible = (
            reviewed == 16
            and successful == len(turns) == 26
            and counts["pass"] >= 14
            and diagnostics["critical_errors"] == 0
            and not capture.get("budget_fault")
        )
        summaries.append(
            {
                "key": key,
                "execution_status": model["status"],
                "verdicts": counts,
                "reviewed_conversations": reviewed,
                "completed_conversations": sum(
                    c["status"] == "completed" for c in cases
                ),
                "http_successful": successful,
                "http_attempted": len(attempted),
                "http_planned": 26,
                "http_not_executed": len(turns) - len(attempted),
                "diagnostics": diagnostics
                if reviewed == sum(c["status"] == "completed" for c in cases)
                else None,
                "diagnostics_reviewed_only": diagnostics,
                "provider_attempts": len(main_attempts),
                "model_responses": sum(
                    t.get("model_trace", {}).get("usage", {}).get("requests", 0)
                    for t in attempted
                ),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": sum(u["cache_read_tokens"] for u in known_usage),
                "cache_write_tokens": sum(u["cache_write_tokens"] for u in known_usage),
                "missing_usage_requests": len(main_attempts) - len(known_usage),
                "http_errors": sum(
                    isinstance(t.get("http_status"), int) and t["http_status"] >= 400
                    for t in attempted
                ),
                "failure_categories": {
                    category: sum(
                        t.get("failure_category") == category for t in attempted
                    )
                    for category in sorted(
                        {
                            str(t["failure_category"])
                            for t in attempted
                            if t.get("failure_category")
                        }
                    )
                },
                "output_validation_retries": sum(
                    t.get("output_validation_retries", 0) for t in attempted
                ),
                "reasoning_tokens_reported": sum(
                    t.get("model_trace", {}).get("usage", {}).get("reasoning_tokens")
                    or 0
                    for t in attempted
                ),
                "estimated_main_usd": str(cost),
                "estimated_preflight_usd": str(preflight_cost),
                "usd_per_pass": str(cost / counts["pass"]) if counts["pass"] else None,
                "median_latency_seconds": statistics.median(latencies)
                if latencies
                else None,
                "max_latency_seconds": max(latencies) if latencies else None,
                "eligible": eligible,
            }
        )
    eligible_models = [s for s in summaries if s["eligible"]]

    def ranking(s: dict[str, Any]) -> tuple[Any, ...]:
        return (
            -s["verdicts"]["pass"],
            s["verdicts"]["fail"],
            s["verdicts"]["partial"],
            s["diagnostics"]["missing_reads"] + s["diagnostics"]["incorrect_arguments"],
            Decimal(s["usd_per_pass"]),
            s["median_latency_seconds"],
            s["key"] != "gpt6_luna",
            KEYS.index(s["key"]),
        )

    winner = (
        min(eligible_models, key=ranking)["key"]
        if eligible_models and not pending
        else None
    )
    return {
        "benchmark": IDENTITY,
        "review_method": method,
        "status": pending_label
        if pending
        else "ai_review_complete"
        if ai_authorized
        else "review_complete",
        "selection": pending_label if pending else winner or "no eligible winner",
        "estimated_total_usd": capture["estimated_spend_usd"],
        "models": summaries,
        "matrix": matrix,
    }


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# Standalone final model comparison",
        "",
        f"Status: **{result['status']}**.",
        "",
        f"Selection: **{result['selection']}**. Runtime default unchanged.",
        "",
        f"Estimated total including preflight and unknown-usage reservations: **US${result['estimated_total_usd']}**.",
        "",
        "Semantic verdicts are a user-authorized, unblinded AI assessment without independent human review. Human worksheets remain available."
        if result.get("review_method") == "ai_user_authorized"
        else "Semantic verdicts require actual human reviews. Pending cells are not passes or failures.",
        "",
        "| Model | Pass / Partial / Fail | Reviewed / completed / 16 | HTTP success / attempted / 26 | Main / preflight USD | Input / output tokens | Provider attempts / missing usage | Median / max latency (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in result["models"]:
        counts = s["verdicts"]
        lines.append(
            f"| {s['key']} | {counts['pass']} / {counts['partial']} / {counts['fail']} | {s['reviewed_conversations']} / {s['completed_conversations']} / 16 | {s['http_successful']} / {s['http_attempted']} / 26 | {s['estimated_main_usd']} / {s['estimated_preflight_usd']} | {s['input_tokens']} / {s['output_tokens']} | {s['provider_attempts']} / {s['missing_usage_requests']} | {s['median_latency_seconds']} / {s['max_latency_seconds']} |"
        )
    lines += [
        "",
        "## Scenario matrix",
        "",
        "| Scenario | " + " | ".join(KEYS) + " |",
        "| --- | " + " | ".join(["---"] * len(KEYS)) + " |",
    ]
    for scenario, row in result["matrix"].items():
        lines.append(
            "| " + scenario + " | " + " | ".join(row[key] for key in KEYS) + " |"
        )
    lines += [
        "",
        "## Limits",
        "",
        "One targeted regression pass, not a statistical superiority claim or a blind holdout. Fixed RAG and unchanged production agent; no prompt tuning or model substitution. Execution failures and unexecuted turns remain in reliability counts. Costs are conservative estimates, not invoices. "
        + (
            "The owner waived human/independent second review after capture. Semantic judgments and selection are provisional AI findings; the original blank human forms remain available for later review."
            if result.get("review_method") == "ai_user_authorized"
            else "Tool/grounding/UX judgments and a final recommendation require the protocol's completed human reviews."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument(
        "--review-file",
        type=Path,
        help="Separate submitted assessment file; human worksheet stays untouched",
    )
    parser.add_argument(
        "--aliases-file",
        type=Path,
        help="Assessment's candidate mapping; defaults to private human aliases",
    )
    parser.add_argument(
        "--allow-ai-review",
        action="store_true",
        help="Apply an explicitly owner-authorized AI assessment, labeled separately from human review",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Fresh report directory after submitted judgments change",
    )
    args = parser.parse_args()
    capture = json.loads((args.run_dir / "capture.json").read_text())
    if args.prepare:
        prepare_review(capture, args.run_dir)
    review = json.loads((args.review_file or args.run_dir / "review.json").read_text())
    aliases = json.loads(
        (args.aliases_file or args.run_dir / "review-aliases.json").read_text()
    )
    result = aggregate(capture, review, aliases, allow_ai=args.allow_ai_review)
    output = args.output_dir or args.run_dir
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "summary.json", result, exclusive=True)
    with (output / "results.md").open("x", encoding="utf-8") as stream:
        stream.write(markdown_report(result))
    print(result["selection"])


if __name__ == "__main__":
    main()
