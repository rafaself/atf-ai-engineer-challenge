"""Explicit environment configuration without loading dotenv files or credentials."""

import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from emporio_music_backend.contracts import NonblankText
from emporio_music_backend.contracts.errors import ConfigurationError


class AgentSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: NonblankText = "amazon.nova-micro-v1:0"
    region: NonblankText = "us-east-1"
    aws_profile: NonblankText | None = None
    request_timeout_seconds: float = Field(
        default=15, gt=0, le=120, allow_inf_nan=False
    )
    max_requests: int = Field(default=5, ge=1, le=20, strict=True)
    max_tool_calls: int = Field(default=5, ge=1, le=20, strict=True)
    max_output_tokens: int = Field(default=1024, ge=64, le=4096, strict=True)

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "AgentSettings":
        env = os.environ if environment is None else environment
        try:
            values: dict[str, object] = {}
            for variable, field in (
                ("BEDROCK_MODEL_ID", "model_id"),
                ("AWS_PROFILE", "aws_profile"),
                ("AWS_DEFAULT_REGION", "region"),
            ):
                if variable in env:
                    values[field] = env[variable]
            if "AWS_DEFAULT_REGION" not in env and "AWS_REGION" in env:
                values["region"] = env["AWS_REGION"]
            for variable, field in (
                ("AGENT_MAX_REQUESTS", "max_requests"),
                ("AGENT_MAX_TOOL_CALLS", "max_tool_calls"),
                ("AGENT_MAX_OUTPUT_TOKENS", "max_output_tokens"),
            ):
                if variable in env:
                    values[field] = int(env[variable])
            if "AGENT_REQUEST_TIMEOUT_SECONDS" in env:
                values["request_timeout_seconds"] = float(
                    env["AGENT_REQUEST_TIMEOUT_SECONDS"]
                )
            return cls.model_validate(values)
        except (ValueError, ValidationError) as exc:
            raise ConfigurationError("Invalid agent environment configuration") from exc
