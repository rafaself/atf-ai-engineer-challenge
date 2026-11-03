"""Opt-in fixed-corpus benchmark: python -m scripts.policy_benchmark.run."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from emporio_music.infrastructure.policy_index import PolicyIndex
from emporio_music.paths import DATA_DIRECTORY
from emporio_music.policies.corpus import (
    FREIGHT_CLARIFICATION_SOURCE,
    PolicyCorpus,
)

from scripts.policy_benchmark.embeddings import MODELS, RATES, Embedder
from scripts.policy_benchmark.evaluation import query_families, score, summarize


def load_inputs() -> tuple[PolicyCorpus, list[dict[str, Any]], dict[str, Any]]:
    directory = DATA_DIRECTORY / "policies"
    corpus = PolicyCorpus.model_validate_json((directory / "corpus.json").read_text())
    freeze = json.loads((directory / "freeze.json").read_text())
    questions_path = directory / freeze["questions_source"]
    questions_bytes = questions_path.read_bytes()
    historical_questions_bytes = (
        directory / freeze["historical_questions_source"]
    ).read_bytes()
    chunks_hash = hashlib.sha256(
        json.dumps(
            [chunk.model_dump(exclude_none=True) for chunk in corpus.chunks],
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()
    pdf_hash = hashlib.sha256(
        (DATA_DIRECTORY / "store_policies.pdf").read_bytes()
    ).hexdigest()
    freight_clarification_hash = hashlib.sha256(
        (DATA_DIRECTORY / FREIGHT_CLARIFICATION_SOURCE).read_bytes()
    ).hexdigest()
    if (
        chunks_hash != freeze["chunks_sha256"]
        or hashlib.sha256(questions_bytes).hexdigest() != freeze["questions_sha256"]
        or hashlib.sha256(historical_questions_bytes).hexdigest()
        != freeze["historical_questions_sha256"]
        or pdf_hash != corpus.source_sha256
        or pdf_hash != freeze["source_sha256"]
        or freeze["freight_clarification_source"] != FREIGHT_CLARIFICATION_SOURCE
        or freight_clarification_hash != corpus.freight_clarification_sha256
        or freight_clarification_hash != freeze["freight_clarification_sha256"]
        or corpus.parser_version != freeze["parser_version"]
    ):
        raise ValueError(
            "Frozen source/corpus/dataset mismatch; review before benchmarking"
        )
    dataset = json.loads(questions_bytes)
    ids = {c.id for c in corpus.chunks if c.indexable}
    if (
        dataset["source_sha256"] != pdf_hash
        or dataset["freight_clarification_sha256"] != freight_clarification_hash
        or any(
            not set(group) <= ids
            for q in dataset["questions"]
            for group in q["evidence_groups"]
        )
    ):
        raise ValueError("Dataset references invalid evidence")
    return corpus, list(dataset["questions"]), freeze


def run(args: argparse.Namespace, report: dict[str, Any]) -> None:
    corpus, questions, freeze = load_inputs()
    chunks = [chunk for chunk in corpus.chunks if chunk.indexable]
    questions = [q for q in questions if q["split"] == args.split]
    report.update(
        freeze=freeze,
        split=args.split,
        questions=len(questions),
        chunks=len(chunks),
        validation_policy="No tuning after validation results; frozen query rules v1",
        embedding_input="hierarchy joined by newline + newline + section text",
        strategy_rule="query-family-union-v1",
        repeats=args.repeats,
    )
    started = time.perf_counter()
    embedder = Embedder(
        args.model,
        allow_download=args.allow_download,
        allow_paid=args.allow_paid,
        region=args.region,
        budget=args.budget_usd,
    )
    report["model_load_seconds"] = time.perf_counter() - started
    config = {
        **embedder.config,
        "source_sha256": corpus.source_sha256,
        "freight_clarification_sha256": corpus.freight_clarification_sha256,
        "corpus_sha256": freeze["chunks_sha256"],
        "parser_version": corpus.parser_version,
        "embedding_input": report["embedding_input"],
    }
    report["configuration"] = config
    index = PolicyIndex(args.index_dir, f"policy-{args.model}", config)
    try:
        if args.index:
            if index.exists() and not args.rebuild:
                raise ValueError(
                    "Index exists; omit --index to reuse or pass --rebuild"
                )
            started = time.perf_counter()
            vectors = embedder.embed(
                ["\n".join(c.hierarchy) + "\n" + c.text for c in chunks], query=False
            )
            report["document_embedding_seconds"] = time.perf_counter() - started
            started = time.perf_counter()
            index.build(chunks, vectors, rebuild=args.rebuild)
            report["index_write_seconds"] = time.perf_counter() - started
            report["document_input_tokens_or_bound"] = embedder.tokens
        else:
            index.open([c.id for c in chunks])
            report["document_embedding_seconds"] = None
            report["index_write_seconds"] = None
        rows: list[dict[str, Any]] = []
        report["rows"] = rows
        for question in questions:
            families = query_families(question["question"])
            samples: dict[str, list[float]] = {
                "embedding": [],
                "vector": [],
                "filtered": [],
            }
            rankings: dict[str, list[str]] = {}
            for _ in range(args.repeats):
                started = time.perf_counter()
                vector = embedder.embed([question["question"]], query=True)[0]
                samples["embedding"].append(time.perf_counter() - started)
                for strategy, filter_families in [
                    ("vector", []),
                    ("filtered", families),
                ]:
                    started = time.perf_counter()
                    ranked = index.search(vector, filter_families)
                    samples[strategy].append(time.perf_counter() - started)
                    if strategy in rankings and rankings[strategy] != ranked:
                        report.setdefault("unstable_rankings", []).append(
                            {"id": question["id"], "strategy": strategy}
                        )
                    rankings[strategy] = ranked
            relevant = (
                set().union(*map(set, question["evidence_groups"]))
                if question["evidence_groups"]
                else set()
            )
            rows.append(
                {
                    "id": question["id"],
                    "question": question["question"],
                    "groups": len(question["evidence_groups"]),
                    "critical": question["critical"],
                    "filter_families": families,
                    "latency_seconds": samples,
                    "rankings": rankings,
                    "evidence_lost_by_filter": sorted(
                        (set(rankings["vector"]) & relevant) - set(rankings["filtered"])
                    ),
                    "metrics": {
                        s: score(r, question["evidence_groups"])
                        for s, r in rankings.items()
                    },
                }
            )
            print(f"{args.model} {args.split} {question['id']} complete", flush=True)
        report["summary"] = {
            strategy: summarize(
                [{**row, "scores": row["metrics"][strategy]} for row in rows]
            )
            for strategy in ["vector", "filtered"]
        }
        report["status"] = "complete"
    finally:
        report["usage"] = {
            "provider_calls": embedder.calls,
            "input_tokens_or_estimate": embedder.tokens,
            "input_token_counts_or_bounds": embedder.token_counts,
            "estimated_usd": embedder.tokens * RATES[args.model] / 1000,
            "reserved_upper_usd_including_failed_calls": embedder.reserved_usd,
            "rate_usd_per_1k": RATES[args.model],
            "price_checked": "2026-11-01",
            "cost_limit_usd": args.budget_usd,
            "billing_limitations": "E5 local tokenizer count; Titan returned token count; local electricity excluded",
        }
        report["index_directory_bytes"] = sum(
            p.stat().st_size for p in args.index_dir.rglob("*") if p.is_file()
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument(
        "--split", choices=["development", "validation"], default="development"
    )
    parser.add_argument("--final-validation", action="store_true")
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--budget-usd", type=float, default=0.10)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--index-dir", type=Path, default=DATA_DIRECTORY / "policy-indexes"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=DATA_DIRECTORY.parent / "docs" / "benchmarks"
    )
    args = parser.parse_args()
    if args.repeats < 1 or args.repeats > 10 or not 0 < args.budget_usd <= 1:
        parser.error("repeats must be 1..10 and budget must be >0 and <= US$1")
    if args.rebuild and not args.index:
        parser.error("--rebuild requires --index")
    if args.split == "validation" and not args.final_validation:
        parser.error(
            "--final-validation is required to acknowledge the held-out boundary"
        )
    report: dict[str, Any] = {
        "started_utc": datetime.now(UTC).isoformat(),
        "model": args.model,
        "status": "failed",
        "hardware": platform.platform(),
        "processor": platform.processor(),
        "versions": {
            name: importlib.metadata.version(name) for name in ["chromadb", "boto3"]
        },
    }
    for package in ["sentence-transformers", "transformers", "torch"]:
        try:
            report["versions"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report["versions"][package] = "not installed"
    try:
        run(args, report)
    except Exception as exc:
        report["error"] = {
            "class": type(exc).__name__,
            "message": str(exc)
            if isinstance(exc, ValueError)
            else "Model/provider unavailable; no score inferred",
        }
    report["finished_utc"] = datetime.now(UTC).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"{args.model}-{args.split}-{time.time_ns()}.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"{report['status']}: {output}", flush=True)
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
