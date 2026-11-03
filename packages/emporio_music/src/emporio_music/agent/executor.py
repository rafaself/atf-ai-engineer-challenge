"""Run the configured agent and translate provider failures to domain errors."""

from botocore.exceptions import (  # type: ignore[import-untyped]
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
    ProfileNotFound,
)
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.exceptions import AgentRunError, ModelAPIError, ModelTimeoutError
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.usage import UsageLimits

from emporio_music.agent.settings import AgentSettings
from emporio_music.diagnostics import trace
from emporio_music.domain.chat import AgentResponse, ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    ProviderUnavailableError,
)


class PydanticAgentExecutor:
    def __init__(
        self, agent: Agent[ExecutionContext, str], settings: AgentSettings
    ) -> None:
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
            "agent.started",
            model=self.settings.model_id,
            aws_region=self.settings.aws_region,
        )
        try:
            result = await self.agent.run(
                validated.message,
                deps=validated_context,
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
