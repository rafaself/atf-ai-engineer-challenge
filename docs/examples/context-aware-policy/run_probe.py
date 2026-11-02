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

import emporio_music_backend.agent.factory as factory
from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.policies import LocalPolicySearch
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.api.app import create_app
from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music_backend.paths import (
    CATALOG_DATABASE_PATH,
    OPERATIONS_DATABASE_PATH,
)
from scripts.compare_models import (
    _code_freeze,
    load_project_aws_environment,
    load_verified_candidates,
    turn_reservation_usd,
)
from scripts.validate_us18 import RecordingAgent, _write_checkpoint

CASES = {
    "hours_context_switch": {
        "turns": [
            {"message": "Qual é o horário normal de funcionamento da loja?"},
            {"message": "E nos feriados e no Natal, há atendimento?"},
            {"message": "O Takamine GD20 está disponível? Qual é o preço e o estoque?"},
        ]
    },
    "missing_policy": {
        "turns": [
            {"message": "O Takamine GD20 está disponível? Qual é o preço e o estoque?"},
            {"message": "E qual é o prazo de arrependimento para uma compra online?"},
        ]
    },
}


async def run(output: Path, variant: str, instructions: str) -> None:
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
    cases = CASES
    factory.STORE_INSTRUCTIONS = instructions
    turns = sum(len(c["turns"]) for c in cases.values())
    reserve = turn_reservation_usd(candidate)
    if turns != 5 or 4 * turns * reserve > Decimal("0.75"):
        raise ValueError("Four-variant reservation exceeds new approval")
    report = {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "issue": 70,
        "purpose": "Context-aware use and conditional reasoning controlled comparison",
        "variant": variant,
        "evaluated_instructions": instructions,
        "all_variants_reserved_upper_usd": str(4 * turns * reserve),
        "source": _code_freeze(),
        "model": settings.model_id,
        "region": settings.aws_region,
        "limits": {"requests": 5, "tool_calls": 5, "output_tokens": 1024},
        "approved_cap_usd": "0.75",
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
                    "criteria": "protocol.md: tool appropriateness and faithfulness separately",
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
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("Explicit --live and owner approval required")
    variants = json.loads((Path(__file__).parent / "variants.json").read_text())[
        "instructions"
    ]
    if list(variants) != ["baseline", "context_only", "conditional_only", "combined"]:
        raise ValueError("Unexpected variant set")
    for variant, instructions in variants.items():
        asyncio.run(run(args.output_dir / (variant + ".json"), variant, instructions))
