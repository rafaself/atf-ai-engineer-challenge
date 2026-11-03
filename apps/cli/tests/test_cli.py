import asyncio
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from emporio_music.application.chat import ChatService
from emporio_music.domain.chat import AgentResponse, ChatRequest
from emporio_music.domain.conversations import (
    ExecutionContext,
    HistoryLimits,
)
from emporio_music.domain.errors import (
    ProviderUnavailableError,
    SessionAccessError,
)
from emporio_music.domain.identity import CustomerIdentity
from emporio_music.infrastructure.catalog_import import import_catalog
from emporio_music.infrastructure.conversations import (
    SQLiteConversationRepository,
)
from emporio_music.infrastructure.operations_import import import_operations
from emporio_music.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_cli.cli import main, run_cli
from pydantic import UUID4


class ControlledAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[ChatRequest, ExecutionContext]] = []

    async def run(
        self, request: ChatRequest, *, context: ExecutionContext
    ) -> AgentResponse:
        self.calls.append((request, context))
        return AgentResponse(answer=f"Resposta: {request.message}")


@pytest.fixture
def order_repository(tmp_path: Path) -> SQLiteOrderRepository:
    data = Path(__file__).resolve().parents[3] / "data"
    catalog = tmp_path / "catalog.sqlite3"
    operations = tmp_path / "operations.sqlite3"
    import_catalog(
        data / "catalog" / "products.csv",
        data / "catalog" / "categories.csv",
        data / "catalog" / "promotions.csv",
        catalog,
    )
    import_operations(
        data / "operations" / "customers.csv",
        data / "operations" / "orders.csv",
        data / "operations" / "order_items.csv",
        catalog,
        operations,
    )
    return SQLiteOrderRepository(operations)


def _input(values: list[str]) -> Callable[[str], str]:
    remaining = iter(values)
    return lambda _prompt: next(remaining)


def test_cli_uses_one_fixed_identity_across_sessions_and_persists_history(
    tmp_path: Path, order_repository: SQLiteOrderRepository
) -> None:
    conversations_path = tmp_path / "conversations.sqlite3"
    conversations = SQLiteConversationRepository(conversations_path)
    agent = ControlledAgent()
    service = ChatService(agent, conversations)
    output: list[str] = []
    prompts: list[str] = []
    inputs = iter(["Primeira", "Segunda", "/new", "Terceira", "/exit"])

    def input_fn(prompt: str) -> str:
        prompts.append(prompt)
        return next(inputs)

    exit_code = run_cli(
        service,
        order_repository,
        input_fn=input_fn,
        output_fn=output.append,
    )

    assert exit_code == 0
    assert (
        output.count(
            "Demonstração com dados fictícios. As consultas simulam os sistemas da loja."
        )
        == 1
    )
    assert prompts == ["Você: "] * 5
    assert len(agent.calls) == 3
    (
        (first_request, first_context),
        (second_request, second_context),
        (
            third_request,
            third_context,
        ),
    ) = agent.calls
    assert first_context.session is not None
    assert third_context.session is not None
    assert first_request.session_id is None
    assert second_request.session_id == first_context.session.session_id
    assert third_request.session_id is None
    fixed_identity = CustomerIdentity(customer_id=1)
    assert first_context.identity == fixed_identity
    assert second_context.identity == fixed_identity
    assert len(first_context.history) == 0
    assert [message.content for message in second_context.history] == [
        "Primeira",
        "Resposta: Primeira",
    ]
    assert third_context.identity == fixed_identity
    assert third_context.history == ()
    fixed_session_id = first_context.session.session_id
    new_session_id = third_context.session.session_id
    assert fixed_session_id != new_session_id

    reopened = SQLiteConversationRepository(conversations_path)
    first_history = reopened.load(
        fixed_session_id, fixed_identity, limits=HistoryLimits()
    ).history
    new_history = reopened.load(
        new_session_id, fixed_identity, limits=HistoryLimits()
    ).history
    assert [message.content for message in first_history] == [
        "Primeira",
        "Resposta: Primeira",
        "Segunda",
        "Resposta: Segunda",
    ]
    assert [message.content for message in new_history] == [
        "Terceira",
        "Resposta: Terceira",
    ]
    with pytest.raises(SessionAccessError):
        asyncio.run(
            service.chat(
                ChatRequest(message="cross-customer", session_id=fixed_session_id),
                context=ExecutionContext(identity=CustomerIdentity(customer_id=2)),
            )
        )
    assert not any("convidado" in line.lower() for line in output)


def test_cli_reports_application_failure_without_leaking_or_resubmitting(
    tmp_path: Path, order_repository: SQLiteOrderRepository
) -> None:
    conversations = SQLiteConversationRepository(tmp_path / "conversations.sqlite3")
    calls: list[ChatRequest] = []
    failed_sessions: list[UUID4] = []

    class FailingAgent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            calls.append(request)
            assert context.session is not None
            failed_sessions.append(context.session.session_id)
            raise ProviderUnavailableError("private provider response")

    output: list[str] = []
    exit_code = run_cli(
        ChatService(FailingAgent(), conversations),
        order_repository,
        input_fn=_input(["pergunta", "/exit"]),
        output_fn=output.append,
    )

    assert exit_code == 0
    assert len(calls) == 1
    assert len(failed_sessions) == 1
    assert (
        conversations.load(
            failed_sessions[0],
            CustomerIdentity(customer_id=1),
            limits=HistoryLimits(),
        ).history
        == ()
    )
    rendered = "\n".join(output)
    assert "indisponível" in rendered
    assert "private provider response" not in rendered
    assert "Traceback" not in rendered


@pytest.mark.parametrize("failure", [EOFError, KeyboardInterrupt])
def test_cli_exits_cleanly_on_eof_and_ctrl_c(
    failure: type[BaseException],
    tmp_path: Path,
    order_repository: SQLiteOrderRepository,
) -> None:
    def interrupted(_prompt: str) -> str:
        raise failure

    output: list[str] = []
    assert (
        run_cli(
            ChatService(
                ControlledAgent(),
                SQLiteConversationRepository(tmp_path / "chat.sqlite3"),
            ),
            order_repository,
            input_fn=interrupted,
            output_fn=output.append,
        )
        == 0
    )
    assert output == [
        "Empório da Música — /new inicia outra conversa; /exit encerra.",
        "Demonstração com dados fictícios. As consultas simulam os sistemas da loja.",
        "Atendimento com identidade fictícia fixa.",
        "\nAté logo.",
    ]


def test_help_and_missing_live_opt_in_do_not_construct_the_service(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from emporio_music import composition

    def unexpected_build(*_args: object) -> None:
        raise AssertionError("the default service must stay behind --live")

    monkeypatch.setattr(composition, "build_chat_service", unexpected_build)
    monkeypatch.setattr(composition, "create_order_repository", unexpected_build)
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    assert "--live" in capsys.readouterr().out

    with pytest.raises(SystemExit) as opt_in_exit:
        main([])
    assert opt_in_exit.value.code == 2
    assert "--live" in capsys.readouterr().err


def test_import_and_help_do_not_load_provider_or_http_modules() -> None:
    source = "\n".join(
        (
            "import sys",
            "sys.path.insert(0, 'cli/src')",
            "from emporio_music_cli.cli import main",
            "try:",
            "    main(['--help'])",
            "except SystemExit as exit:",
            "    assert exit.code == 0",
            "assert not {'boto3', 'botocore', 'pydantic_ai', 'fastapi', "
            "'chromadb', 'sentence_transformers'} & sys.modules.keys()",
        )
    )
    subprocess.run(
        [sys.executable, "-c", source],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
