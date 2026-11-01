"""Sanitized HTTP responses for validation, application and unexpected failures."""

from fastapi.responses import JSONResponse

from emporio_music_backend.contracts.errors import (
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    CustomerSelectionError,
    PolicyRetrievalError,
    ProviderUnavailableError,
    SessionAccessError,
    SessionConflictError,
)


def application_failure_handler(exc: ApplicationError) -> JSONResponse:
    if isinstance(exc, CustomerSelectionError):
        return JSONResponse(
            status_code=422,
            content={"detail": "Unknown demo customer"},
        )
    if isinstance(exc, SessionAccessError):
        return JSONResponse(
            status_code=404, content={"detail": "Conversation session unavailable"}
        )
    if isinstance(exc, SessionConflictError):
        return JSONResponse(
            status_code=409, content={"detail": "Conversation turn conflicts"}
        )
    if isinstance(exc, AgentTimeoutError):
        return JSONResponse(
            status_code=504, content={"detail": "Conversation timed out"}
        )
    if isinstance(
        exc, (ConfigurationError, PolicyRetrievalError, ProviderUnavailableError)
    ):
        return JSONResponse(
            status_code=503, content={"detail": "Agent service unavailable"}
        )
    return JSONResponse(status_code=500, content={"detail": "Conversation failed"})


def invalid_request_handler() -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid chat request"})


def unexpected_failure_handler() -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
