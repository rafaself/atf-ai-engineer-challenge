"""Interactive terminal adapter for the shared chat application."""

import argparse
import asyncio
import sys
from collections.abc import Callable, Sequence

from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.domain.errors import (
    AgentTimeoutError,
    ApplicationError,
    ConfigurationError,
    ConversationPersistenceError,
    PolicyRetrievalError,
    ProviderUnavailableError,
    SessionAccessError,
    SessionConflictError,
)
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music.ports.chat import ChatServicePort
from pydantic import UUID4, ValidationError

InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emporio-music-chat",
        description="Converse com o agente local do Empório da Música.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="opt in to live Bedrock requests, which may incur charges",
    )
    return parser


def _error_message(error: ApplicationError) -> str:
    if isinstance(error, SessionAccessError):
        return "Esta conversa não está disponível. Use /new para iniciar outra."
    if isinstance(error, SessionConflictError):
        return "Já existe uma resposta em andamento nesta conversa."
    if isinstance(error, AgentTimeoutError):
        return "A solicitação excedeu o tempo limite."
    if isinstance(error, ConfigurationError):
        return "A configuração local está incompleta. Verifique os dados preparados e o acesso ao Bedrock."
    if isinstance(error, ProviderUnavailableError):
        return "O Bedrock está indisponível no momento."
    if isinstance(error, PolicyRetrievalError):
        return "A busca de políticas está indisponível; os arquivos locais podem não estar preparados."
    if isinstance(error, ConversationPersistenceError):
        return "Não foi possível confirmar o salvamento da conversa."
    return "Não foi possível concluir a mensagem. Nenhuma resposta foi confirmada."


async def _chat_loop(
    chat_service: ChatServicePort,
    order_repository: SQLiteOrderRepository,
    input_fn: InputFunction,
    output_fn: OutputFunction,
) -> None:
    from emporio_music.composition import get_fixed_demo_identity

    output_fn("Empório da Música — /new inicia outra conversa; /exit encerra.")
    output_fn(
        "Demonstração com dados fictícios. As consultas simulam os sistemas da loja."
    )
    output_fn("Atendimento com identidade fictícia fixa.")
    session_id: UUID4 | None = None
    while True:
        message = input_fn("Você: ").strip()
        command = message.casefold()
        if command in {"/exit", "exit", "quit"}:
            return
        if command == "/new":
            output_fn("Nova conversa.")
            session_id = None
            continue
        if not message:
            continue
        try:
            request = ChatRequest(message=message, session_id=session_id)
        except ValidationError:
            output_fn("A mensagem deve ter entre 1 e 4000 caracteres.")
            continue
        try:
            identity = get_fixed_demo_identity(order_repository)
            response = await chat_service.chat(
                request,
                context=ExecutionContext(identity=identity),
            )
        except ApplicationError as error:
            output_fn(f"Erro: {_error_message(error)}")
            continue
        session_id = response.session_id
        output_fn(f"Assistente: {response.answer}")


def run_cli(
    chat_service: ChatServicePort,
    order_repository: SQLiteOrderRepository,
    *,
    input_fn: InputFunction = input,
    output_fn: OutputFunction = print,
) -> int:
    """Run an injected service; this entry is also used by offline tests."""
    try:
        asyncio.run(_chat_loop(chat_service, order_repository, input_fn, output_fn))
    except (EOFError, KeyboardInterrupt):
        output_fn("\nAté logo.")
        return 0
    except ApplicationError as error:
        output_fn(f"Erro: {_error_message(error)}")
        return 1
    output_fn("Até logo.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    if not arguments.live:
        parser.error("use --live to opt in to Bedrock-backed conversation")

    try:
        from emporio_music.composition import (
            build_chat_service,
            create_order_repository,
        )

        orders = create_order_repository()
        service = build_chat_service(orders)
    except ApplicationError as error:
        print(f"Erro: {_error_message(error)}", file=sys.stderr)
        return 1
    return run_cli(service, orders)


if __name__ == "__main__":
    raise SystemExit(main())
