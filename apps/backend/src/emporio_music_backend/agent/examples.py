"""Explicitly paid example recorder; captured output still requires human review."""

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.usage import UsageLimits

from emporio_music_backend.agent.catalog import create_catalog_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts.catalog import ProductSearchQuery
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)

SCENARIOS = (
    ("01-budget", "Quais violões disponíveis custam até R$ 1.000?"),
    ("02-named-product", "Qual o preço e estoque do Takamine GD20?"),
    (
        "03-unavailable",
        "Consulte o Giannini GF-3D mesmo se estiver indisponível. Posso comprar agora?",
    ),
    ("04-no-matches", "Vocês têm um instrumento chamado ZXQ-999-Inexistente?"),
    ("05-out-of-scope", "Qual será a previsão do tempo amanhã em Paris?"),
)


def snapshot_identity(database: Path) -> str:
    with database.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


async def record(database: Path, output: Path) -> None:
    """Capture real SDK messages, never replacing a missing trace with invented data."""
    settings = AgentSettings.from_environment()
    identity = snapshot_identity(database)
    repository = SQLiteProductRepository(database)
    repository.search(ProductSearchQuery(limit=1))
    executor = create_catalog_agent(settings, repository)
    captured: list[tuple[str, str]] = []
    for name, prompt in SCENARIOS:
        async with asyncio.timeout(60):
            result = await executor.agent.run(
                prompt,
                deps=ExecutionContext(),
                usage_limits=UsageLimits(
                    request_limit=settings.max_requests,
                    tool_calls_limit=settings.max_tool_calls,
                ),
            )
        trace: list[dict[str, object]] = []
        for message in result.all_messages():
            for part in message.parts:
                if isinstance(part, ToolCallPart):
                    trace.append(
                        {
                            "kind": "call",
                            "tool": part.tool_name,
                            "call_id": part.tool_call_id,
                            "arguments": part.args_as_dict(),
                        }
                    )
                elif isinstance(part, ToolReturnPart):
                    trace.append(
                        {
                            "kind": "return",
                            "tool": part.tool_name,
                            "call_id": part.tool_call_id,
                            "result": part.content,
                        }
                    )
        metadata = {
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "model": settings.model_id,
            "region": settings.region,
            "pydantic_ai": version("pydantic-ai-slim"),
            "boto3": version("boto3"),
            "database_sha256": identity,
            "requests": result.usage.requests,
        }
        document = (
            f"# Live capture: {name}\n\n"
            "Review status: pending human grounding and scope review.\n"
            "A capture is evidence of execution, not an automatic acceptance pass.\n\n"
            f"## Metadata\n\n```json\n{json.dumps(metadata, indent=2)}\n```\n\n"
            f"## User\n\n{prompt}\n\n"
            f"## Actual tool trace\n\n```json\n"
            f"{json.dumps(trace, ensure_ascii=False, indent=2)}\n```\n\n"
            f"## Actual answer\n\n{result.output}\n"
        )
        captured.append((name, document))
    if snapshot_identity(database) != identity:
        raise RuntimeError("Catalog changed during capture; no evidence saved")
    output.mkdir(parents=True, exist_ok=True)
    for name, document in captured:
        with (output / f"{name}.md").open("x", encoding="utf-8") as destination:
            destination.write(document)
    print(
        f"Saved {len(captured)} live captures to {output}; review each before acceptance"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Opt-in paid live conversation recorder"
    )
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; this command incurs real Bedrock requests")
    if not args.database.is_file():
        parser.error("Import the catalog first; --database must be an existing file")
    if args.output_dir.exists() and not args.output_dir.is_dir():
        parser.error("--output-dir must be a directory")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error(
            "--output-dir must be empty or absent; existing evidence is preserved"
        )
    try:
        asyncio.run(record(args.database, args.output_dir))
    except Exception as exc:
        parser.exit(
            1, f"Live capture failed ({type(exc).__name__}); no acceptance claimed\n"
        )


if __name__ == "__main__":
    main()
