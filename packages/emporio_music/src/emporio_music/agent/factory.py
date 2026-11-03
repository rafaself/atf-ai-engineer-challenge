"""Construct the configured Pydantic AI agent and Bedrock model."""

from collections.abc import Sequence

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import BotoCoreError, ClientError  # type: ignore[import-untyped]
from pydantic_ai import Agent, Tool
from pydantic_ai.models import Model
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

from emporio_music.agent.executor import PydanticAgentExecutor
from emporio_music.agent.output import customer_answer
from emporio_music.agent.persona import STORE_INSTRUCTIONS
from emporio_music.agent.settings import AgentSettings
from emporio_music.diagnostics import failure, trace
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.errors import ConfigurationError


def create_agent(
    settings: AgentSettings,
    *,
    model: Model | None = None,
    tools: Sequence[Tool[ExecutionContext]] = (),
) -> PydanticAgentExecutor:
    """Construct explicitly, using an injected test model without AWS setup."""
    injected_model = model is not None
    if model is None:
        trace(
            "provider.initializing",
            model=settings.model_id,
            aws_region=settings.aws_region,
            explicit_profile=settings.aws_profile is not None,
        )
        try:
            session = boto3.Session(
                profile_name=settings.aws_profile, region_name=settings.aws_region
            )
            client = session.client(
                "bedrock-runtime",
                config=Config(
                    connect_timeout=5,
                    read_timeout=settings.request_timeout_seconds,
                    retries={"mode": "standard", "total_max_attempts": 1},
                ),
            )
            model = BedrockConverseModel(
                settings.model_id, provider=BedrockProvider(bedrock_client=client)
            )
        except (BotoCoreError, ClientError, ValueError) as exc:
            trace("provider.failure", **failure(exc))
            raise ConfigurationError(
                "Cannot initialize Bedrock; check AWS profile, region and credentials"
            ) from exc
    trace(
        "provider.ready",
        configured_model=settings.model_id,
        aws_region=settings.aws_region,
        injected_model=injected_model,
    )
    agent = Agent[ExecutionContext, str](
        model,
        deps_type=ExecutionContext,
        instructions=STORE_INSTRUCTIONS,
        tools=tools,
        retries={"tools": 0, "output": 1},
        model_settings={
            "max_tokens": settings.max_output_tokens,
            "temperature": 0,
            "request_timeout": settings.request_timeout_seconds,
        },
    )
    agent.output_validator(customer_answer)
    return PydanticAgentExecutor(agent, settings)
