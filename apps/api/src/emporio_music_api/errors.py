"""Sanitized HTTP responses for validation, application and unexpected failures."""

from emporio_music.domain.errors import (
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    PolicyRetrievalError,
    ProviderUnavailableError,
    SessionAccessError,
    SessionConflictError,
)
from fastapi.responses import JSONResponse


def application_failure_response(exc: ApplicationError) -> tuple[int, str]:
    if isinstance(exc, SessionAccessError):
        return 404, "Conversation session unavailable"
    if isinstance(exc, SessionConflictError):
        return 409, "Conversation turn conflicts"
    if isinstance(exc, AgentTimeoutError):
        return 504, "Conversation timed out"
    if isinstance(
        exc, (ConfigurationError, PolicyRetrievalError, ProviderUnavailableError)
    ):
        return 503, "Agent service unavailable"
    return 500, "Conversation failed"


def application_failure_handler(exc: ApplicationError) -> JSONResponse:
    status_code, detail = application_failure_response(exc)
    return JSONResponse(status_code=status_code, content={"detail": detail})


def sanitized_stream_failure(exc: Exception) -> str:
    """Return the existing safe failure detail for an SSE error event."""
    if isinstance(exc, ApplicationError):
        return application_failure_response(exc)[1]
    return "Internal server error"


def invalid_request_handler() -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid chat request"})


def unexpected_failure_handler() -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
