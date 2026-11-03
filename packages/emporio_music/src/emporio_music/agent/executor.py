"""Run the configured agent and translate provider failures to domain errors."""

from collections.abc import AsyncGenerator

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
    FinalResultEvent,
    ModelMessage,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    UserPromptPart,
)
from pydantic_ai.run import AgentRunResultEvent
from pydantic_ai.usage import UsageLimits

from emporio_music.agent.output import release_safe_stream_text
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
from emporio_music.ports.agent import (
    AgentStreamEvent,
    AgentTextDelta,
    StreamingAgentExecutor,
)


def _prepare_run(
    request: ChatRequest, context: ExecutionContext
) -> tuple[ChatRequest, ExecutionContext, list[ModelMessage]]:
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
    return validated, validated_context, history


class PydanticAgentExecutor(StreamingAgentExecutor):
    def __init__(
        self, agent: Agent[ExecutionContext, str], settings: AgentSettings
    ) -> None:
        self.agent = agent
        self.settings = settings

    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        validated, validated_context, history = _prepare_run(request, context)
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

    async def stream(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AsyncGenerator[AgentStreamEvent, None]:
        """Stream selected answer text while the complete agent run executes."""
        validated, validated_context, history = _prepare_run(request, context)
        trace(
            "agent.started",
            model=self.settings.model_id,
            aws_region=self.settings.aws_region,
            streaming=True,
        )
        try:
            async with self.agent.run_stream_events(
                validated.message,
                deps=validated_context,
                message_history=history,
                usage_limits=UsageLimits(
                    request_limit=self.settings.max_requests,
                    tool_calls_limit=self.settings.max_tool_calls,
                ),
            ) as events:
                current_text_part: tuple[int, str] | None = None
                selected_text_index: int | None = None
                pending_text = ""
                suppress_current_text = False
                async for event in events:
                    if isinstance(event, PartStartEvent):
                        current_text_part = None
                        selected_text_index = None
                        pending_text = ""
                        suppress_current_text = False
                        if isinstance(event.part, TextPart):
                            current_text_part = (event.index, event.part.content)
                    elif isinstance(event, FinalResultEvent):
                        if event.tool_name is None and current_text_part is not None:
                            selected_text_index, initial_text = current_text_part
                            released, pending_text, suppress_current_text = (
                                release_safe_stream_text(initial_text)
                            )
                            if released:
                                yield AgentTextDelta(text=released)
                    elif isinstance(event, PartDeltaEvent) and isinstance(
                        event.delta, TextPartDelta
                    ):
                        if (
                            event.index == selected_text_index
                            and not suppress_current_text
                        ):
                            delta = event.delta.content_delta
                            if delta:
                                released, pending_text, suppress_current_text = (
                                    release_safe_stream_text(pending_text + delta)
                                )
                                if released:
                                    yield AgentTextDelta(text=released)
                    elif isinstance(event, AgentRunResultEvent):
                        result = event.result
                        if not suppress_current_text:
                            released, pending_text, _ = release_safe_stream_text(
                                pending_text, final=True
                            )
                            if released:
                                yield AgentTextDelta(text=released)
                        trace(
                            "agent.completed",
                            requests=result.usage.requests,
                            input_tokens=result.usage.input_tokens,
                            output_tokens=result.usage.output_tokens,
                            streaming=True,
                        )
                        yield AgentResponse(answer=result.output)
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
