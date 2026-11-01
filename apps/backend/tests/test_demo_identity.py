"""Only configured, server-owned demo identities can establish session ownership."""

import json

import pytest

from emporio_music_backend.contracts.errors import (
    AuthenticationError,
    ConfigurationError,
)
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.infrastructure.demo_identity import DemoIdentityResolver


class Customers:
    def exists(self, identity: CustomerIdentity) -> bool:
        return identity.customer_id in {1, 2}


TOKEN_A = "synthetic-alice-" + "a" * 32
TOKEN_B = "synthetic-bob-" + "b" * 32


def test_identity_resolution_rejects_forgery_and_does_not_retain_plain_tokens() -> None:
    mapping = {TOKEN_A: 1, TOKEN_B: 2}
    resolver = DemoIdentityResolver(mapping, Customers())
    mapping[TOKEN_A] = 2
    assert resolver.resolve(TOKEN_A).customer_id == 1
    assert resolver.resolve(TOKEN_B).customer_id == 2
    for invalid in (None, "", "1", "unknown-" + "c" * 32, "é" * 32):
        with pytest.raises(AuthenticationError) as error:
            resolver.resolve(invalid)
        assert str(error.value) == "Customer identity required"
    assert TOKEN_A not in repr(vars(resolver))


def test_configuration_is_strict_and_errors_do_not_reveal_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid = json.dumps({TOKEN_A: 1, TOKEN_B: 2})
    for raw in (
        "",
        "[]",
        "{}",
        json.dumps({TOKEN_A: True}),
        json.dumps({TOKEN_A: "1"}),
        '{"' + TOKEN_A + '":1,"' + TOKEN_A + '":2}',
        '{"short":1}',
    ):
        monkeypatch.setenv("DEMO_CUSTOMER_TOKENS_JSON", raw)
        with pytest.raises(ConfigurationError) as error:
            DemoIdentityResolver.from_environment(Customers())
        assert TOKEN_A not in str(error.value)
    monkeypatch.setenv("DEMO_CUSTOMER_TOKENS_JSON", valid)
    assert (
        DemoIdentityResolver.from_environment(Customers()).resolve(TOKEN_B).customer_id
        == 2
    )
