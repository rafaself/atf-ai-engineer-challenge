"""Explicit, bounded live RAG functional check; no full-context competition."""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx
from emporio_music import paths
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.settings import AgentSettings
from emporio_music.application.chat import ChatService
from emporio_music.diagnostics import failure
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music_api.app import create_app

from scripts.evaluation_support import RecordingAgent, write_checkpoint

# Frozen historical accounting assumptions, not current invoice prices. Reserve
# all five requests at the model's 32K input window and 1024 output-token cap,
# even on failures. No SDK retry or experiment retry beyond the agent's limits.
CASE_RESERVE_USD = 5 * (32768 * 0.20 + 1024 * 0.80) / 1_000_000
QWEN_MODEL = "qwen.qwen3-32b-v1:0"


def _progress(event: str, **fields: Any) -> None:
    """Emit only controlled phase names and non-sensitive run metadata."""
    print(
        json.dumps(
            {
                "event": event,
                "recorded_at_utc": datetime.now(UTC).isoformat(),
                **fields,
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
        flush=True,
    )


def _run_status(http_status: int) -> str:
    """Classify non-2xx application results as failed evaluation cases."""
    return "completed" if 200 <= http_status < 300 else "failed"


def _probe_status(runs: list[dict[str, Any]]) -> str:
    """Distinguish a finished probe from one whose cases all succeeded."""
    return (
        "completed_with_failures"
        if any(run.get("status") == "failed" for run in runs)
        else "completed"
    )


def _record_failure(
    report: dict[str, Any],
    run: dict[str, Any] | None,
    evidence: dict[str, Any],
    exc: BaseException,
    elapsed_seconds: float | None,
) -> str:
    """Store safe failure metadata and any partial model/tool evidence."""
    status = (
        "interrupted"
        if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError))
        else "failed"
    )
    safe_failure = failure(exc)
    report["failed_phase"] = report.get("phase")
    report["status"] = status
    report["phase"] = status
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    report["failure"] = safe_failure
    if run is not None:
        run["status"] = status
        run["failure"] = safe_failure
        if elapsed_seconds is not None:
            run["elapsed_seconds"] = round(elapsed_seconds, 3)
        run.update(evidence)
    return status


async def validate(
    output: Path,
    max_cost_usd: float,
    case_id: str | None = None,
) -> None:
    historical = json.loads(
        (paths.DATA_DIRECTORY.parent / "docs/examples/us-17/captures.json").read_text()
    )
    cases = [run for run in historical["runs"] if run["mode"] == "rag"]
    if len(cases) != 4:
        raise ValueError("Expected four frozen US-17 RAG cases")
    if case_id is not None:
        cases = [case for case in cases if case["case_id"] == case_id]
        if len(cases) != 1:
            raise ValueError("Unknown frozen case")
    if not len(cases) * CASE_RESERVE_USD <= max_cost_usd <= 0.25:
        raise ValueError(
            f"Selected cases require a reservation of USD {len(cases) * CASE_RESERVE_USD:.6f}; cap must be <= 0.25"
        )
    settings = AgentSettings(
        model_id=QWEN_MODEL,
        aws_region="us-east-1",
        max_requests=5,
        max_tool_calls=5,
        max_output_tokens=1024,
    )
    # Refuse overwrites before creating an executor or making provider calls.
    with (
        output.open("x") as stream,
        tempfile.TemporaryDirectory(prefix="us18-") as temporary,
    ):
        os.environ["PIPELINE_LOGS"] = "1"
        report: dict[str, Any] = {
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "status": "running",
            "phase": "agent_setup",
            "purpose": "US-18 functional RAG validation, manual source-based review required",
            "model": settings.model_id,
            "region": settings.aws_region,
            "temperature": 0,
            "reasoning_effort": "provider default",
            "max_requests": 5,
            "max_tool_calls": 5,
            "max_output_tokens": 1024,
            "max_cost_usd": max_cost_usd,
            "cost_assumption": "Historical USD/M input 0.20, output 0.80; not invoice pricing",
            "source_freeze": historical["source_freeze"],
            "runs": [],
        }
        current_run: dict[str, Any] | None = None
        request_started: float | None = None
        recorder: RecordingAgent | None = None
        write_checkpoint(stream, report)
        _progress(
            "probe.started",
            model=settings.model_id,
            region=settings.aws_region,
            case_count=len(cases),
            max_requests=settings.max_requests,
            max_tool_calls=settings.max_tool_calls,
            max_output_tokens=settings.max_output_tokens,
            max_cost_usd=max_cost_usd,
        )
        try:
            _progress("agent_setup.started")
            executor = create_store_agent(
                settings,
                SQLiteProductRepository(paths.CATALOG_DATABASE_PATH),
                SQLiteOrderRepository(paths.OPERATIONS_DATABASE_PATH),
            )
            _progress("agent_setup.completed")

            report["phase"] = "chat_service_setup"
            write_checkpoint(stream, report)
            recorder = RecordingAgent(executor)
            service = ChatService(
                recorder,
                SQLiteConversationRepository(Path(temporary) / "chat.sqlite3"),
            )
            # Fresh session per case; all calls traverse the normal HTTP validation
            # and customer selection. The operational databases remain read-only.
            report["phase"] = "http_client_setup"
            write_checkpoint(stream, report)
            _progress("http_client_setup.started")
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(
                    app=create_app(service), raise_app_exceptions=False
                ),
                base_url="http://us18.local",
            ) as client:
                _progress("http_client_setup.completed")
                for case in cases:
                    payload: dict[str, Any] = {"message": case["prompt"]}
                    if case["case_id"] == "mixed-order-return":
                        payload["customer_id"] = 1
                    recorder.evidence = {}
                    current_run = {
                        "case_id": case["case_id"],
                        "prompt": case["prompt"],
                        "status": "in_progress",
                        "started_at_utc": datetime.now(UTC).isoformat(),
                        "reserved_upper_usd": CASE_RESERVE_USD,
                    }
                    report["phase"] = "http_request"
                    report["current_case_id"] = case["case_id"]
                    report["runs"].append(current_run)
                    write_checkpoint(stream, report)
                    _progress("http.request.started", case_id=case["case_id"])
                    request_started = perf_counter()
                    response = await client.post("/api/chat", json=payload)
                    body = response.json()
                    body.pop("session_id", None)
                    current_run.update(
                        {
                            "status": _run_status(response.status_code),
                            "http_status": response.status_code,
                            "http_response": body,
                            "elapsed_seconds": round(
                                perf_counter() - request_started, 3
                            ),
                            **recorder.evidence,
                        }
                    )
                    _progress(
                        "http.response.completed",
                        case_id=case["case_id"],
                        http_status=response.status_code,
                        elapsed_seconds=current_run["elapsed_seconds"],
                    )
                    report.pop("current_case_id", None)
                    report["phase"] = "between_cases"
                    write_checkpoint(stream, report)
                    current_run = None
                    request_started = None

            report["status"] = _probe_status(report["runs"])
            report["phase"] = "completed"
            report["finished_at_utc"] = datetime.now(UTC).isoformat()
            write_checkpoint(stream, report)
            _progress(
                "probe.completed",
                case_count=len(cases),
                failed_case_count=sum(
                    run.get("status") == "failed" for run in report["runs"]
                ),
            )
        except BaseException as exc:
            status = _record_failure(
                report,
                current_run,
                recorder.evidence if recorder is not None else {},
                exc,
                perf_counter() - request_started
                if request_started is not None
                else None,
            )
            write_checkpoint(stream, report)
            _progress(
                "probe.stopped",
                status=status,
                phase=report.get("failed_phase"),
                case_id=report.get("current_case_id"),
                failure_type=type(exc).__name__,
            )
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Requires separate explicit owner approval"
    )
    parser.add_argument("--max-cost-usd", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--case", choices=["hours", "mixed-order-return", "money-unknown", "return"]
    )
    args = parser.parse_args()
    if not args.live:
        parser.error(
            "--live and separate owner approval are required; no calls were made"
        )
    asyncio.run(validate(args.output, args.max_cost_usd, args.case))


if __name__ == "__main__":
    main()
