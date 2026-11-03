"""Validated agent configuration; dotenv loading and credentials stay external."""

from pydantic import AliasChoices, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from emporio_music.domain.base import NonblankText
from emporio_music.domain.errors import ConfigurationError


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True, extra="forbid", populate_by_name=True, case_sensitive=True
    )

    model_id: NonblankText = Field(
        default="qwen.qwen3-32b-v1:0", validation_alias="BEDROCK_MODEL_ID"
    )
    aws_region: NonblankText = Field(
        default="us-east-1",
        validation_alias=AliasChoices("AWS_DEFAULT_REGION", "AWS_REGION"),
    )
    aws_profile: NonblankText | None = Field(
        default=None, validation_alias="AWS_PROFILE"
    )
    request_timeout_seconds: float = Field(
        default=15,
        gt=0,
        le=120,
        allow_inf_nan=False,
        validation_alias="AGENT_REQUEST_TIMEOUT_SECONDS",
    )
    max_requests: int = Field(
        default=5, ge=1, le=20, strict=True, validation_alias="AGENT_MAX_REQUESTS"
    )
    max_tool_calls: int = Field(
        default=5, ge=1, le=20, strict=True, validation_alias="AGENT_MAX_TOOL_CALLS"
    )
    max_output_tokens: int = Field(
        default=1024,
        ge=64,
        le=4096,
        strict=True,
        validation_alias="AGENT_MAX_OUTPUT_TOKENS",
    )

    @field_validator(
        "max_requests", "max_tool_calls", "max_output_tokens", mode="before"
    )
    @classmethod
    def parse_integer_setting(cls, value: object) -> object:
        """Accept integer environment strings without coercing floats or booleans."""
        return int(value) if isinstance(value, str) else value


def load_agent_settings() -> AgentSettings:
    """Load environment configuration with an application-safe failure message."""
    try:
        return AgentSettings()
    except ValidationError as exc:
        raise ConfigurationError("Invalid agent environment configuration") from exc
