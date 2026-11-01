"""Factory-based local HTTP API with lazy, dependency-injected composition."""

import os
from collections.abc import Callable
from functools import lru_cache
from threading import Lock
from time import perf_counter
from typing import Annotated, cast
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from emporio_music_backend import paths
from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.api.errors import (
    application_failure_handler,
    invalid_request_handler,
    unexpected_failure_handler,
)
from emporio_music_backend.api.schemas import DemoChatRequest
from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.contracts.chat import ChatRequest, ChatResponse
from emporio_music_backend.contracts.conversations import (
    ExecutionContext,
    HistoryLimits,
)
from emporio_music_backend.contracts.errors import (
    ApplicationError,
    ConfigurationError,
    CustomerSelectionError,
)
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.diagnostics import failure, request_id, trace
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music_backend.ports.chat import ChatServicePort

ChatServiceFactory = Callable[[], ChatServicePort]


def get_chat_service_factory(request: Request) -> ChatServiceFactory:
    """Return the callable that lazily supplies the chat service."""
    return cast(ChatServiceFactory, request.app.state.chat_service_factory)


def create_app(chat_service: ChatServicePort | None = None) -> FastAPI:
    """Create the local fictional demo; provider setup waits for a valid request."""
    app = FastAPI(title="Empório da Música", version="0.1.0")

    @lru_cache(maxsize=1)
    def customer_repository() -> SQLiteOrderRepository:
        return SQLiteOrderRepository(paths.OPERATIONS_DATABASE_PATH)

    def select_demo_customer(customer_id: int | None) -> CustomerIdentity | None:
        if customer_id is None:
            return None
        identity = CustomerIdentity(customer_id=customer_id)
        if not customer_repository().exists(identity):
            raise CustomerSelectionError("Unknown demo customer")
        return identity

    @lru_cache(maxsize=1)
    def build_chat_service() -> ChatServicePort:
        if chat_service is not None:
            return chat_service
        trace("composition.started")
        agent_settings = AgentSettings.from_environment()
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
                SQLiteProductRepository(paths.CATALOG_DATABASE_PATH),
                SQLiteOrderRepository(paths.OPERATIONS_DATABASE_PATH),
            ),
            SQLiteConversationRepository(paths.CONVERSATION_DATABASE_PATH),
            timeout_seconds=chat_timeout_seconds,
            history_limits=history_limits,
        )

    chat_service_initialization_lock = Lock()

    def chat_service_factory() -> ChatServicePort:
        with chat_service_initialization_lock:
            return build_chat_service()

    app.state.chat_service_factory = chat_service_factory

    @app.exception_handler(RequestValidationError)
    async def invalid_request(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return invalid_request_handler()

    @app.exception_handler(ApplicationError)
    async def application_failure(
        _request: Request, exc: ApplicationError
    ) -> JSONResponse:
        return application_failure_handler(exc)

    @app.exception_handler(Exception)
    async def unexpected_failure(_request: Request, _exc: Exception) -> JSONResponse:
        return unexpected_failure_handler()

    @app.post(
        "/api/chat",
        response_model=ChatResponse,
        responses={
            422: {"description": "Invalid request or unknown demo customer"},
            404: {"description": "Conversation session unavailable"},
            409: {"description": "Conversation turn conflicts"},
            503: {"description": "Agent service unavailable"},
            504: {"description": "Conversation timed out"},
            500: {"description": "Conversation failed"},
        },
    )
    async def chat(
        chat_request: Annotated[
            DemoChatRequest,
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
        chat_service_factory: Annotated[
            ChatServiceFactory, Depends(get_chat_service_factory)
        ],
    ) -> ChatResponse:
        request_id_reset_token = request_id.set(uuid4().hex[:12])
        started = perf_counter()
        try:
            trace("http.request")
            identity = await run_in_threadpool(
                select_demo_customer, chat_request.customer_id
            )
            # SQLite and SDK setup may do I/O; keep it off the event loop.
            chat_service = await run_in_threadpool(chat_service_factory)
            trace("chat.started")
            response = await chat_service.chat(
                ChatRequest.model_validate(
                    chat_request.model_dump(exclude={"customer_id"}, exclude_none=True)
                ),
                context=ExecutionContext(identity=identity),
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
