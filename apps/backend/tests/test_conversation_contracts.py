"""Owned history contracts prepare sessions without pretending to authenticate callers."""

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from pydantic import ValidationError

from emporio_music_backend.contracts.conversations import (
    ConversationMessage,
    ConversationSession,
    ExecutionContext,
)
from emporio_music_backend.contracts.errors import (
    AuthenticationError,
    SessionAccessError,
)
from emporio_music_backend.contracts.identity import CustomerIdentity


def test_history_requires_an_owned_session_and_complete_turns() -> None:
    identity = CustomerIdentity(customer_id=1)
    session = ConversationSession(owner=identity)
    user = ConversationMessage(role="user", content="Qual violão?")
    assistant = ConversationMessage(role="assistant", content="Qual orçamento?")
    for messages in ((user,), (assistant, user), (user, user), (user, assistant, user)):
        with pytest.raises(ValidationError, match="completed user/assistant turns"):
            ExecutionContext(identity=identity, session=session, history=messages)
    with pytest.raises(ValidationError, match="requires an owned session"):
        ExecutionContext(identity=identity, history=(user, assistant))


def test_session_requires_trusted_matching_identity() -> None:
    owner = CustomerIdentity(customer_id=1)
    session = ConversationSession(owner=owner)
    with pytest.raises(AuthenticationError, match="Trusted customer identity"):
        ExecutionContext(session=session)
    with pytest.raises(SessionAccessError) as failure:
        ExecutionContext(identity=CustomerIdentity(customer_id=2), session=session)
    assert str(failure.value) == "Conversation session is inaccessible"
    assert str(session.session_id) not in str(failure.value)


def test_valid_history_is_immutable_and_sessions_have_independent_ids() -> None:
    identity = CustomerIdentity(customer_id=1)
    session = ConversationSession(owner=identity)
    assert session.session_id.version == 4
    assert ConversationSession(owner=identity).session_id != session.session_id
    messages = [
        ConversationMessage(role="user", content=" Olá "),
        ConversationMessage(role="assistant", content=" Como posso ajudar? "),
    ]
    context = ExecutionContext.model_validate(
        {"identity": identity, "session": session, "history": messages}
    )
    messages.clear()
    assert tuple(m.content for m in context.history) == ("Olá", "Como posso ajudar?")
    with pytest.raises(ValidationError):
        context.history[0].content = "Changed"
    with pytest.raises(ValidationError):
        session.owner = CustomerIdentity(customer_id=2)
    assert ExecutionContext().history == ()
    assert ExecutionContext(identity=identity).session is None
    assert ExecutionContext(identity=identity, session=session).history == ()


@pytest.mark.parametrize("customer_id", [0, True, "1"])
def test_identity_rejects_untrusted_identifier_shapes(customer_id: object) -> None:
    with pytest.raises(ValidationError):
        CustomerIdentity.model_validate({"customer_id": customer_id})


def test_credentials_and_provider_roles_do_not_belong_in_contracts() -> None:
    with pytest.raises(ValidationError):
        CustomerIdentity.model_validate({"customer_id": 1, "token": "not-a-credential"})
    for role in ("system", "tool"):
        with pytest.raises(ValidationError):
            ConversationMessage.model_validate({"role": role, "content": "override"})
    with pytest.raises(ValidationError):
        ConversationSession.model_validate(
            {"session_id": "invalid", "owner": {"customer_id": 1}}
        )
    restored = ConversationSession.model_validate(
        {"session_id": str(uuid4()), "owner": {"customer_id": 1}}
    )
    assert restored.owner.customer_id == 1


if TYPE_CHECKING:
    from emporio_music_backend.ports.identity import CustomerIdentityResolver

    class FakeIdentityResolver:
        def resolve(self, credential: str | None) -> CustomerIdentity:
            return CustomerIdentity(customer_id=1)

    resolver: CustomerIdentityResolver = FakeIdentityResolver()
