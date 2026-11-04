"""Factory-based local HTTP API with lazy, dependency-injected composition."""

import json
from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing
from functools import lru_cache
from threading import Lock
from time import perf_counter
from typing import Annotated, cast
from uuid import UUID, uuid4

from emporio_music.composition import (
    build_chat_service as compose_chat_service,
)
from emporio_music.composition import (
    create_order_repository,
    get_fixed_demo_identity,
)
from emporio_music.diagnostics import failure, request_id, trace
from emporio_music.domain.chat import ChatRequest, ChatResponse
from emporio_music.domain.conversations import (
    ConversationSummary,
    ConversationTranscript,
    ExecutionContext,
)
from emporio_music.domain.errors import ApplicationError
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.ports.chat import (
    ChatServicePort,
    ChatStreamDelta,
    ConversationHistoryPort,
    StreamingChatServicePort,
)
from fastapi import Body, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from emporio_music_api import paths as api_paths
from emporio_music_api.errors import (
    application_failure_handler,
    invalid_request_handler,
    sanitized_stream_failure,
    unexpected_failure_handler,
)

ChatServiceFactory = Callable[[], ChatServicePort]


def _sse_event(name: str, data: dict[str, object]) -> str:
    return (
        f"event: {name}\n"
        f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


def get_chat_service_factory(request: Request) -> ChatServiceFactory:
    """Return the callable that lazily supplies the chat service."""
    return cast(ChatServiceFactory, request.app.state.chat_service_factory)


def create_app(chat_service: ChatServicePort | None = None) -> FastAPI:
    """Create the local fictional demo; provider setup waits for a valid request."""
    app = FastAPI(title="Empório da Música", version="0.1.0")

    @lru_cache(maxsize=1)
    def customer_repository() -> SQLiteOrderRepository:
        return create_order_repository()

    def fixed_demo_identity() -> CustomerIdentity:
        return get_fixed_demo_identity(customer_repository())

    @lru_cache(maxsize=1)
    def build_chat_service() -> ChatServicePort:
        if chat_service is not None:
            return chat_service
        return compose_chat_service(customer_repository())

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
            422: {"description": "Invalid chat request"},
            404: {"description": "Conversation session unavailable"},
            409: {"description": "Conversation turn conflicts"},
            503: {"description": "Agent service unavailable"},
            504: {"description": "Conversation timed out"},
            500: {"description": "Conversation failed"},
        },
    )
    async def chat(
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
        chat_service_factory: Annotated[
            ChatServiceFactory, Depends(get_chat_service_factory)
        ],
    ) -> ChatResponse:
        request_id_reset_token = request_id.set(uuid4().hex[:12])
        started = perf_counter()
        try:
            trace("http.request")
            identity = await run_in_threadpool(fixed_demo_identity)
            # SQLite and SDK setup may do I/O; keep it off the event loop.
            chat_service = await run_in_threadpool(chat_service_factory)
            trace("chat.started")
            response = await chat_service.chat(
                chat_request,
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

    @app.post(
        "/api/chat/stream",
        response_class=StreamingResponse,
        responses={
            422: {"description": "Invalid chat request"},
            404: {"description": "Conversation session unavailable"},
            409: {"description": "Conversation turn conflicts"},
            503: {"description": "Agent service unavailable"},
            504: {"description": "Conversation timed out"},
            500: {"description": "Conversation failed"},
        },
    )
    async def chat_stream(
        chat_request: ChatRequest,
        chat_service_factory: Annotated[
            ChatServiceFactory, Depends(get_chat_service_factory)
        ],
    ) -> StreamingResponse:
        stream_request_id = uuid4().hex[:12]
        request_id_reset_token = request_id.set(stream_request_id)
        started = perf_counter()
        try:
            trace("http.request", streaming=True)
            identity = await run_in_threadpool(fixed_demo_identity)
            chat_service = await run_in_threadpool(chat_service_factory)
            request = chat_request
        except Exception as exc:
            trace(
                "http.failure",
                **failure(exc),
                duration_ms=round((perf_counter() - started) * 1000, 1),
                streaming=True,
            )
            raise
        finally:
            request_id.reset(request_id_reset_token)

        async def event_stream() -> AsyncGenerator[str, None]:
            token = request_id.set(stream_request_id)
            completed = False
            try:
                trace("chat.stream.started")
                service_events = cast(StreamingChatServicePort, chat_service).stream(
                    request, context=ExecutionContext(identity=identity)
                )
                async with aclosing(service_events) as events:
                    async for event in events:
                        if isinstance(event, ChatStreamDelta):
                            yield _sse_event("delta", {"text": event.text})
                        else:
                            completed = True
                            yield _sse_event("done", event.model_dump(mode="json"))
                            break
                if not completed:
                    raise RuntimeError("Chat stream ended without a final response")
            except Exception as exc:
                trace(
                    "http.failure",
                    **failure(exc),
                    duration_ms=round((perf_counter() - started) * 1000, 1),
                    streaming=True,
                )
                yield _sse_event("error", {"message": sanitized_stream_failure(exc)})
            finally:
                trace(
                    "http.response",
                    status=200,
                    duration_ms=round((perf_counter() - started) * 1000, 1),
                    streaming=True,
                    completed=completed,
                )
                request_id.reset(token)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/conversations", response_model=list[ConversationSummary])
    async def list_conversations(
        chat_service_factory: Annotated[
            ChatServiceFactory, Depends(get_chat_service_factory)
        ],
    ) -> list[ConversationSummary]:
        identity = await run_in_threadpool(fixed_demo_identity)
        service = cast(
            ConversationHistoryPort,
            await run_in_threadpool(chat_service_factory),
        )
        return list(await run_in_threadpool(service.list_conversations, identity))

    @app.get("/api/conversations/{session_id}", response_model=ConversationTranscript)
    async def get_conversation(
        session_id: UUID,
        chat_service_factory: Annotated[
            ChatServiceFactory, Depends(get_chat_service_factory)
        ],
    ) -> ConversationTranscript:
        identity = await run_in_threadpool(fixed_demo_identity)
        service = cast(
            ConversationHistoryPort,
            await run_in_threadpool(chat_service_factory),
        )
        return await run_in_threadpool(service.get_conversation, session_id, identity)

    @app.delete("/api/conversations/{session_id}", status_code=204)
    async def delete_conversation(
        session_id: UUID,
        chat_service_factory: Annotated[
            ChatServiceFactory, Depends(get_chat_service_factory)
        ],
    ) -> Response:
        identity = await run_in_threadpool(fixed_demo_identity)
        service = cast(
            ConversationHistoryPort,
            await run_in_threadpool(chat_service_factory),
        )
        await run_in_threadpool(service.delete_conversation, session_id, identity)
        return Response(status_code=204)

    frontend_index = api_paths.FRONTEND_DIRECTORY / "index.html"
    frontend_assets = api_paths.FRONTEND_DIRECTORY / "assets"
    if frontend_assets.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=frontend_assets),
            name="frontend-assets",
        )
    if frontend_index.is_file():

        @app.get("/", include_in_schema=False)
        async def frontend_index_page() -> FileResponse:
            return FileResponse(frontend_index)

    return app
