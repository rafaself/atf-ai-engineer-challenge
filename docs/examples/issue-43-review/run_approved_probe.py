"""One-off approved Qwen probe; reuse #40 cases and US-18 trace capture."""

import argparse
import asyncio
import json
import tempfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter

import httpx

from emporio_music.agent.orders import create_store_agent
from emporio_music.policies.search import LocalPolicySearch
from emporio_music.agent.settings import AgentSettings
from emporio_music_api.app import create_app
from emporio_music.application.chat import ChatService
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music.paths import (
    CATALOG_DATABASE_PATH,
    OPERATIONS_DATABASE_PATH,
)
from scripts.compare_models import (
    _code_freeze,
    load_project_aws_environment,
    load_scenarios,
    load_verified_candidates,
    turn_reservation_usd,
)
from scripts.validate_us18 import RecordingAgent, _write_checkpoint

SELECTED = (
    "named-stock-alternative",
    "promotion-pix",
    "selected-orders-list-detail",
    "mixed-order-return-followup",
    "policy-hours-context-topic-change",
    "freight-exact-threshold",
)


async def run(output: Path) -> None:
    load_project_aws_environment()
    settings = AgentSettings()
    assert (settings.model_id, settings.aws_region) == (
        "qwen.qwen3-32b-v1:0",
        "us-east-1",
    )
    assert (
        settings.max_requests,
        settings.max_tool_calls,
        settings.max_output_tokens,
    ) == (5, 5, 1024)
    candidate = next(
        c for c in load_verified_candidates() if c.model_id == settings.model_id
    )
    cases = {c["id"]: c for c in load_scenarios()}
    cases = {key: cases[key] for key in SELECTED}
    turns = sum(len(c["turns"]) for c in cases.values())
    reserve = turn_reservation_usd(candidate)
    assert turns == 12 and turns * reserve <= Decimal("0.50")
    report = {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "issue": 70,
        "purpose": "Approved post-#43 Qwen-only functional sample; manual review required",
        "source": _code_freeze(),
        "model": settings.model_id,
        "region": settings.aws_region,
        "limits": {"requests": 5, "tool_calls": 5, "output_tokens": 1024},
        "approved_cap_usd": "0.50",
        "reserved_upper_usd": str(turns * reserve),
        "input_usd_per_million": str(candidate.input_usd_per_million),
        "output_usd_per_million": str(candidate.output_usd_per_million),
        "pricing_source": "docs/examples/model-comparison/pricing.json (verified same day)",
        "retrieval": "Cached E5/index preflight on same search instance; policy calls are warm",
        "status": "preflight",
        "cases": [],
    }
    with (
        output.open("x") as stream,
        tempfile.TemporaryDirectory(prefix="issue43-probe-") as temp,
    ):
        _write_checkpoint(stream, report)
        search = LocalPolicySearch()
        search.search("Frete para entrega em Campo Grande de R$ 500?")
        agent = RecordingAgent(
            create_store_agent(
                settings,
                SQLiteProductRepository(CATALOG_DATABASE_PATH),
                SQLiteOrderRepository(OPERATIONS_DATABASE_PATH),
                policy_search=search,
            )
        )
        service = ChatService(
            agent, SQLiteConversationRepository(Path(temp) / "chat.sqlite3")
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(
                app=create_app(service), raise_app_exceptions=False
            ),
            base_url="http://approved-probe.local",
        ) as client:
            for key, case in cases.items():
                current = {
                    "id": key,
                    "baseline_expected": case["expected"],
                    "turns": [],
                }
                report["cases"].append(current)
                session = None
                for prompt in case["turns"]:
                    payload = dict(prompt)
                    if "customer_id" in case:
                        payload["customer_id"] = case["customer_id"]
                    if session:
                        payload["session_id"] = session
                    agent.evidence = {}
                    row = {"prompt": prompt["message"], "status": "started"}
                    current["turns"].append(row)
                    report["status"] = "running"
                    _write_checkpoint(stream, report)
                    started = perf_counter()
                    response = await client.post("/api/chat", json=payload)
                    body = response.json()
                    session = body.pop("session_id", None)
                    row.update(
                        status="completed",
                        http_status=response.status_code,
                        seconds=round(perf_counter() - started, 3),
                        response=body,
                        **agent.evidence,
                    )
                    _write_checkpoint(stream, report)
                    print(
                        json.dumps(
                            {
                                "case": key,
                                "turn": len(current["turns"]),
                                "http_status": response.status_code,
                            }
                        ),
                        flush=True,
                    )
                    if response.status_code != 200:
                        break  # Preserve the failed turn; do not retry that conversation.
        report["status"] = "finished"
        _write_checkpoint(stream, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("Explicit --live and owner approval required")
    asyncio.run(run(args.output))
