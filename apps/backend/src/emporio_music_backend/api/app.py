"""Factory-based local HTTP API with lazy, dependency-injected composition."""

import os
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.contracts.chat import ChatRequest, ChatResponse
from emporio_music_backend.contracts.conversations import (
    ExecutionContext,
    HistoryLimits,
)
from emporio_music_backend.contracts.errors import (
    AgentTimeoutError,
    ApplicationError,
    AuthenticationError,
    ConfigurationError,
    ProviderUnavailableError,
    SessionAccessError,
    SessionConflictError,
)
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.diagnostics import failure, request_id, trace
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.infrastructure.demo_identity import DemoIdentityResolver
from emporio_music_backend.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music_backend.ports.chat import ChatServicePort
from emporio_music_backend.ports.identity import CustomerIdentityResolver

ChatServiceFactory = Callable[[], ChatServicePort]
IdentityResolverFactory = Callable[[], CustomerIdentityResolver]
_bearer = HTTPBearer(auto_error=False)


def get_chat_service_factory(request: Request) -> ChatServiceFactory:
    """Return the callable that lazily supplies the chat service."""
    return cast(ChatServiceFactory, request.app.state.chat_service_factory)


def get_identity_resolver_factory(request: Request) -> IdentityResolverFactory:
    return cast(IdentityResolverFactory, request.app.state.identity_resolver_factory)


def resolve_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    identity_resolver_factory: Annotated[
        IdentityResolverFactory, Depends(get_identity_resolver_factory)
    ],
) -> CustomerIdentity:
    if credentials is None:
        raise AuthenticationError("Customer identity required")
    return identity_resolver_factory().resolve(credentials.credentials)


def _database_paths() -> tuple[Path, Path, Path]:
    paths = tuple(
        Path(os.environ.get(key, default)).resolve()
        for key, default in (
            ("DATABASE_PATH", "data/catalog.sqlite3"),
            ("OPERATIONS_DATABASE_PATH", "data/operations.sqlite3"),
            ("CONVERSATION_DATABASE_PATH", "data/conversations.sqlite3"),
        )
    )
    for index, path in enumerate(paths):
        for other in paths[index + 1 :]:
            if path == other or (
                path.exists() and other.exists() and path.samefile(other)
            ):
                raise ConfigurationError(
                    "Catalog, operations and conversation storage must be separate"
                )
    return paths[0], paths[1], paths[2]


def create_app(
    chat_service: ChatServicePort | None = None,
    *,
    identity_resolver: CustomerIdentityResolver | None = None,
) -> FastAPI:
    """Create a local API; provider/database setup is deferred until a valid chat."""
    app = FastAPI(title="Empório da Música", version="0.1.0")

    @lru_cache(maxsize=1)
    def identity_resolver_factory() -> CustomerIdentityResolver:
        return (
            identity_resolver
            if identity_resolver is not None
            else DemoIdentityResolver.from_environment(
                SQLiteOrderRepository(_database_paths()[1])
            )
        )

    app.state.identity_resolver_factory = identity_resolver_factory
    chat_service_initialization_lock = Lock()

    @lru_cache(maxsize=1)
    def build_chat_service() -> ChatServicePort:
        if chat_service is not None:
            return chat_service
        trace("composition.started")
        agent_settings = AgentSettings.from_environment()
        catalog_database_path, operations_database_path, conversation_database_path = (
            _database_paths()
        )
        try:
            chat_timeout_seconds = float(os.environ.get("CHAT_TIMEOUT_SECONDS", "60"))
            history_limits = HistoryLimits(
                max_turns=int(os.environ.get("HISTORY_MAX_TURNS", "6")),
                max_characters=int(os.environ.get("HISTORY_MAX_CHARACTERS", "24000")),
            )
        except ValueError as exc:
            raise ConfigurationError("Invalid conversation limits") from exc
        return ChatService(
            create_store_agent(
                agent_settings,
                SQLiteProductRepository(catalog_database_path),
                SQLiteOrderRepository(operations_database_path),
            ),
            SQLiteConversationRepository(conversation_database_path),
            timeout_seconds=chat_timeout_seconds,
            history_limits=history_limits,
        )

    def chat_service_factory() -> ChatServicePort:
        # lru_cache alone can invoke initialization concurrently on cache misses.
        with chat_service_initialization_lock:
            return build_chat_service()

    app.state.chat_service_factory = chat_service_factory

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "Invalid chat request"})

    @app.exception_handler(ApplicationError)
    async def application_failure(
        request: Request, exc: ApplicationError
    ) -> JSONResponse:
        if isinstance(exc, AuthenticationError):
            return JSONResponse(
                status_code=401,
                content={"detail": "Customer identity required"},
                headers={"WWW-Authenticate": "Bearer"},
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
        chat_request: Annotated[
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
        identity: Annotated[CustomerIdentity, Depends(resolve_identity)],
        chat_service_factory: Annotated[
            ChatServiceFactory, Depends(get_chat_service_factory)
        ],
    ) -> ChatResponse:
        request_id_reset_token = request_id.set(uuid4().hex[:12])
        started = perf_counter()
        try:
            trace("http.request")
            # SDK credential resolution may do I/O; keep it off the event loop.
            chat_service = await run_in_threadpool(chat_service_factory)
            trace("chat.started")
            response = await chat_service.chat(
                chat_request, context=ExecutionContext(identity=identity)
            )
            trace(
                "http.response",
                status=200,
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
            request_id.reset(request_id_reset_token)

    return app
