"""Opt-in live Bedrock probe; prints evidence only after a verified tool round trip."""

import argparse
import asyncio
import json
import secrets
from importlib.metadata import version

from pydantic_ai import Tool
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.usage import UsageLimits

from emporio_music_backend.agent.factory import create_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts.conversations import ExecutionContext


async def probe() -> dict[str, object]:
    settings = AgentSettings.from_environment()
    code = "verificado-" + secrets.token_hex(4)

    def verify_store_integration() -> str:
        """Return a fresh code to verify this store assistant's tool integration."""
        return code

    executor = create_agent(settings, tools=[Tool(verify_store_integration)])
    result = await executor.agent.run(
        "Teste técnico autorizado da integração da loja: consulte verify_store_integration "
        "e responda com o código exato retornado pela ferramenta.",
        deps=ExecutionContext(),
        usage_limits=UsageLimits(request_limit=3, tool_calls_limit=1),
    )
    parts = [part for message in result.all_messages() for part in message.parts]
    called = any(
        isinstance(part, ToolCallPart) and part.tool_name == "verify_store_integration"
        for part in parts
    )
    returned = any(
        isinstance(part, ToolReturnPart) and part.content == code for part in parts
    )
    if not (called and returned and code in result.output):
        raise RuntimeError("Live model did not complete the required tool round trip")
    return {
        "model": settings.model_id,
        "region": settings.region,
        "pydantic_ai_version": version("pydantic-ai-slim"),
        "boto3_version": version("boto3"),
        "tool": "verify_store_integration",
        "arguments": {},
        "tool_result": code,
        "answer": result.output,
        "requests": result.usage.requests,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Opt-in paid Bedrock tool-calling probe"
    )
    parser.add_argument("--live", action="store_true")
    if not parser.parse_args().live:
        parser.error(
            "--live is required; configure AWS_PROFILE/credentials before running"
        )
    print(json.dumps(asyncio.run(probe()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
