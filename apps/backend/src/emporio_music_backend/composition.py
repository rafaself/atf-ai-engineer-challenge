"""Transport-neutral composition shared by the HTTP and terminal adapters."""

import os

from emporio_music_backend import paths
from emporio_music_backend.agent.orders import create_store_agent
from emporio_music_backend.agent.settings import load_agent_settings
from emporio_music_backend.application.chat import ChatService
from emporio_music_backend.contracts.conversations import HistoryLimits
from emporio_music_backend.contracts.errors import (
    ConfigurationError,
    CustomerSelectionError,
)
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.diagnostics import trace
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music_backend.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)


def create_order_repository() -> SQLiteOrderRepository:
    """Open the existing operations snapshot for customer and order access."""
    return SQLiteOrderRepository(paths.OPERATIONS_DATABASE_PATH)


def resolve_demo_customer(
    customer_id: int | None,
    order_repository: SQLiteOrderRepository | None = None,
) -> CustomerIdentity | None:
    """Validate an optional fictional customer against the imported registry."""
    if customer_id is None:
        return None
    identity = CustomerIdentity(customer_id=customer_id)
    repository = (
        create_order_repository() if order_repository is None else order_repository
    )
    if not repository.exists(identity):
        raise CustomerSelectionError("Unknown demo customer")
    return identity


def build_chat_service(
    order_repository: SQLiteOrderRepository | None = None,
) -> ChatService:
    """Compose the existing agent, repositories and chat service once requested."""
    trace("composition.started")
    agent_settings = load_agent_settings()
    try:
        chat_timeout_seconds = float(os.environ.get("CHAT_TIMEOUT_SECONDS", "60"))
        history_limits = HistoryLimits(
            max_turns=int(os.environ.get("HISTORY_MAX_TURNS", "6")),
            max_characters=int(os.environ.get("HISTORY_MAX_CHARACTERS", "24000")),
        )
    except ValueError as exc:
        raise ConfigurationError("Invalid conversation limits") from exc

    orders = create_order_repository() if order_repository is None else order_repository
    return ChatService(
        create_store_agent(
            agent_settings,
            SQLiteProductRepository(paths.CATALOG_DATABASE_PATH),
            orders,
        ),
        SQLiteConversationRepository(paths.CONVERSATION_DATABASE_PATH),
        timeout_seconds=chat_timeout_seconds,
        history_limits=history_limits,
    )
