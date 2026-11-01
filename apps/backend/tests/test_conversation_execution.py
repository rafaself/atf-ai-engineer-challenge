"""Explicit trusted histories must reach the model without cross-run state."""

import asyncio

import pytest
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from emporio_music_backend.agent.factory import create_agent
from emporio_music_backend.agent.settings import AgentSettings
from emporio_music_backend.application import ChatService
from emporio_music_backend.contracts import (
    AgentResponse,
    ChatRequest,
    ConversationMessage,
    ConversationSession,
    CustomerIdentity,
    ExecutionContext,
)
from emporio_music_backend.contracts.errors import SessionAccessError
from emporio_music_backend.infrastructure.conversations import (
    SQLiteConversationRepository,
)


def owned_context(customer_id: int, topic: str) -> ExecutionContext:
    identity = CustomerIdentity(customer_id=customer_id)
    return ExecutionContext(
        identity=identity,
        session=ConversationSession(owner=identity),
        history=(
            ConversationMessage(role="user", content=topic),
            ConversationMessage(role="assistant", content="Qual seu orçamento?"),
        ),
    )


def test_service_propagates_independent_contexts_without_mutating_them(
    conversations: SQLiteConversationRepository,
) -> None:
    contexts = [owned_context(1, "Violões"), owned_context(2, "Teclados")]
    contexts = [
        ExecutionContext(
            identity=c.identity,
            session=conversations.create(c.identity),
            history=c.history,
        )
        for c in contexts
        if c.identity
    ]
    for c in contexts:
        assert c.session
        conversations.append(
            c.session, 0, user_message=c.history[0].content, answer=c.history[1].content
        )
    observed: list[ExecutionContext] = []

    class Agent:
        async def run(
            self, request: ChatRequest, *, context: ExecutionContext
        ) -> AgentResponse:
            observed.append(context)
            await asyncio.sleep(0)
            return AgentResponse(answer="Resposta de controle")

    async def exercise() -> None:
        service = ChatService(Agent(), conversations)
        await asyncio.gather(
            *(
                service.chat(
                    ChatRequest(message="Até R$1000", session_id=c.session.session_id),
                    context=ExecutionContext(identity=c.identity),
                )
                for c in contexts
                if c.session
            )
        )

    asyncio.run(exercise())
    assert observed == contexts
    assert contexts[0].history[0].content == "Violões"
    assert contexts[1].history[0].content == "Teclados"


def test_adapter_translates_text_history_per_run_without_identity_metadata() -> None:
    observed: list[tuple[str, ...]] = []

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        text: list[str] = []
        for message in messages:
            for part in message.parts:
                assert isinstance(part, (UserPromptPart, TextPart))
                assert isinstance(part.content, str)
                text.append(part.content)
        observed.append(tuple(text))
        await asyncio.sleep(0)
        return ModelResponse(parts=[TextPart("Resposta de controle")])

    executor = create_agent(AgentSettings(), model=FunctionModel(respond))
    contexts = [owned_context(8181, "Violões"), owned_context(9292, "Teclados")]

    async def exercise() -> None:
        results = await asyncio.gather(
            *(
                executor.run(ChatRequest(message="Até R$1000"), context=c)
                for c in contexts
            )
        )
        assert all(result.answer == "Resposta de controle" for result in results)
        await executor.run(
            ChatRequest(message="Nova consulta"), context=ExecutionContext()
        )

    asyncio.run(exercise())
    assert set(observed[:2]) == {
        ("Violões", "Qual seu orçamento?", "Até R$1000"),
        ("Teclados", "Qual seu orçamento?", "Até R$1000"),
    }
    assert observed[2] == ("Nova consulta",)
    assert all(
        str(c.session.session_id) not in repr(observed) for c in contexts if c.session
    )
    assert "8181" not in repr(observed) and "9292" not in repr(observed)


def test_service_and_direct_adapter_revalidate_ownership_before_model_call(
    conversations: SQLiteConversationRepository,
) -> None:
    def forbidden(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise AssertionError("The model must not receive a foreign history")

    executor = create_agent(AgentSettings(), model=FunctionModel(forbidden))
    valid = owned_context(1, "Private history")
    forged = ExecutionContext.model_construct(
        identity=CustomerIdentity(customer_id=2),
        session=valid.session,
        history=valid.history,
    )

    async def exercise() -> None:
        for runner in (executor.run, ChatService(executor, conversations).chat):
            with pytest.raises(
                SessionAccessError, match="Conversation session is inaccessible"
            ):
                await runner(ChatRequest(message="Continue"), context=forged)

    asyncio.run(exercise())
