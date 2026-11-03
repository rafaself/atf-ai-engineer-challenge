"""Transport-neutral composition shared by the HTTP and terminal adapters."""

import os

from emporio_music import paths
from emporio_music.agent.orders import create_store_agent
from emporio_music.agent.settings import load_agent_settings
from emporio_music.application.chat import ChatService
from emporio_music.diagnostics import trace
from emporio_music.domain.conversations import HistoryLimits
from emporio_music.domain.errors import (
    ConfigurationError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)

DEMO_CUSTOMER_ID = 1


def create_order_repository() -> SQLiteOrderRepository:
    """Open the existing operations snapshot for customer and order access."""
    return SQLiteOrderRepository(paths.OPERATIONS_DATABASE_PATH)


def get_fixed_demo_identity(
    order_repository: SQLiteOrderRepository | None = None,
) -> CustomerIdentity:
    """Return the fixed fictional demo identity after checking the current snapshot."""
    identity = CustomerIdentity(customer_id=DEMO_CUSTOMER_ID)
    repository = (
        create_order_repository() if order_repository is None else order_repository
    )
    if not repository.exists(identity):
        raise ConfigurationError("The fixed demo customer is missing from the snapshot")
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
    get_fixed_demo_identity(orders)
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
