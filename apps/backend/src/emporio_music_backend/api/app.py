"""Factory-based local HTTP API with lazy, dependency-injected composition."""

import os
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from emporio_music_backend.agent.catalog import create_catalog_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.application import ChatService, ChatServicePort
from emporio_music_backend.contracts import ChatRequest, ChatResponse, ExecutionContext
from emporio_music_backend.contracts.errors import (
    AgentTimeoutError,
    ApplicationError,
    AuthenticationError,
    ConfigurationError,
    ProviderUnavailableError,
    SessionAccessError,
    SessionConflictError,
)
from emporio_music_backend.diagnostics import failure, request_id, trace
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)

ServiceFactory = Callable[[], ChatServicePort]


def get_service_factory(request: Request) -> ServiceFactory:
    """Return a constructor without resolving credentials before payload validation."""
    return cast(ServiceFactory, request.app.state.service_factory)


def create_app(service: ChatServicePort | None = None) -> FastAPI:
    """Create a local API; provider/database setup is deferred until a valid chat."""
    app = FastAPI(title="Empório da Música", version="0.1.0")

    @lru_cache(maxsize=1)
    def service_factory() -> ChatServicePort:
        if service is not None:
            return service
        trace("composition.started")
        settings = AgentSettings.from_environment()
        database = Path(os.environ.get("DATABASE_PATH", "data/catalog.sqlite3"))
        try:
            timeout = float(os.environ.get("CHAT_TIMEOUT_SECONDS", "60"))
        except ValueError as exc:
            raise ConfigurationError("Invalid conversation timeout") from exc
        return ChatService(
            create_catalog_agent(settings, SQLiteProductRepository(database)),
            timeout_seconds=timeout,
        )

    app.state.service_factory = service_factory

    @app.exception_handler(ApplicationError)
    async def application_failure(
        request: Request, exc: ApplicationError
    ) -> JSONResponse:
        if isinstance(exc, AuthenticationError):
            return JSONResponse(
                status_code=401, content={"detail": "Customer identity required"}
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
        if isinstance(exc, (ConfigurationError, ProviderUnavailableError)):
            return JSONResponse(
                status_code=503, content={"detail": "Agent service unavailable"}
            )
        return JSONResponse(status_code=500, content={"detail": "Conversation failed"})

    @app.exception_handler(Exception)
    async def unexpected_failure(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    @app.post(
        "/api/chat",
        response_model=ChatResponse,
        responses={
            401: {"description": "Customer identity required"},
            404: {"description": "Conversation session unavailable"},
            409: {"description": "Conversation turn conflicts"},
            503: {"description": "Agent service unavailable"},
            504: {"description": "Conversation timed out"},
            500: {"description": "Conversation failed"},
        },
    )
    async def chat(
        request: Request,
        message: Annotated[
            ChatRequest,
            Body(
                openapi_examples={
                    "catalog": {
                        "summary": "Look up a catalog product",
                        "value": {
                            "message": "Qual o preço e estoque do Takamine GD20?"
                        },
                    }
                }
            ),
        ],
        factory: Annotated[ServiceFactory, Depends(get_service_factory)],
    ) -> ChatResponse:
        token = request_id.set(uuid4().hex[:12])
        started = perf_counter()
        try:
            trace("http.request", message=message.message)
            # SDK credential resolution may do I/O; keep it off the event loop.
            chat_service = await run_in_threadpool(factory)
            trace("chat.started")
            # US-09 HTTP remains stateless; trusted identity/session resolution is US-10.
            response = await chat_service.chat(message, context=ExecutionContext())
            trace(
                "http.response",
                status=200,
                answer=response.answer,
                duration_ms=round((perf_counter() - started) * 1000, 1),
            )
            return response
        except Exception as exc:
            trace(
                "http.failure",
                **failure(exc),
                duration_ms=round((perf_counter() - started) * 1000, 1),
            )
            raise
        finally:
            request_id.reset(token)

    return app
