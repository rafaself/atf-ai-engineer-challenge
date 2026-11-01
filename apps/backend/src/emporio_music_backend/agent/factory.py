"""Pydantic AI construction and provider-specific exception translation."""

from collections.abc import Sequence

import boto3  # type: ignore[import-untyped]
from botocore.config import Config  # type: ignore[import-untyped]
from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
    ProfileNotFound,
)
from pydantic import ValidationError
from pydantic_ai import Agent, Tool
from pydantic_ai.exceptions import AgentRunError, ModelAPIError, ModelTimeoutError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models import Model
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai.usage import UsageLimits

from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.agent.persona import STORE_INSTRUCTIONS
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.contracts import AgentResponse, ChatRequest, ExecutionContext
from emporio_music_backend.contracts.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    ProviderUnavailableError,
)
from emporio_music_backend.diagnostics import failure, trace


class PydanticAgentExecutor:
    def __init__(self, agent: Agent[None, str], settings: AgentSettings) -> None:
        self.agent = agent
        self.settings = settings

    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        validated = ChatRequest.model_validate(request)
        validated_context = ExecutionContext.model_validate(context)
        # Only conversational text crosses the provider boundary, never identity,
        # ownership metadata, credentials or old tool returns. Each run owns its list.
        history: list[ModelMessage] = [
            ModelRequest(parts=[UserPromptPart(message.content)])
            if message.role == "user"
            else ModelResponse(parts=[TextPart(message.content)])
            for message in validated_context.history
        ]
        trace(
            "agent.started", model=self.settings.model_id, region=self.settings.region
        )
        try:
            result = await self.agent.run(
                validated.message,
                message_history=history,
                usage_limits=UsageLimits(
                    request_limit=self.settings.max_requests,
                    tool_calls_limit=self.settings.max_tool_calls,
                ),
            )
            trace(
                "agent.completed",
                requests=result.usage.requests,
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
            )
            return AgentResponse(answer=result.output)
        except ApplicationError:
            raise
        except (ModelTimeoutError, TimeoutError) as exc:
            raise AgentTimeoutError("Model request timed out") from exc
        except (NoCredentialsError, PartialCredentialsError, ProfileNotFound) as exc:
            raise ConfigurationError(
                "Configure an AWS profile or credential chain for Bedrock"
            ) from exc
        except (ModelAPIError, BotoCoreError, ClientError) as exc:
            raise ProviderUnavailableError(
                "Bedrock could not serve the request"
            ) from exc
        except (AgentRunError, ValidationError) as exc:
            raise AgentExecutionError(
                "Agent execution did not produce a valid answer"
            ) from exc


def create_agent(
    settings: AgentSettings,
    *,
    model: Model | None = None,
    tools: Sequence[Tool[None]] = (),
) -> PydanticAgentExecutor:
    """Construct explicitly, using a supplied test/alternative model without AWS setup."""
    injected_model = model is not None
    if model is None:
        trace(
            "provider.initializing",
            model=settings.model_id,
            region=settings.region,
            explicit_profile=settings.aws_profile is not None,
        )
        try:
            session = boto3.Session(
                profile_name=settings.aws_profile, region_name=settings.region
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
        region=settings.region,
        injected_model=injected_model,
    )
    agent = Agent[None, str](
        model,
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
