"""Explicit local demo identity mapping; not production authentication."""

import hashlib
import hmac
import json
import os
import re
from collections.abc import Mapping

from pydantic import ValidationError

from emporio_music_backend.contracts import CustomerIdentity
from emporio_music_backend.contracts.errors import (
    AuthenticationError,
    ConfigurationError,
)

_TOKEN = re.compile(r"[A-Za-z0-9_-]{32,256}\Z", re.ASCII)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate identity mapping key")
        result[key] = value
    return result


class DemoIdentityResolver:
    def __init__(self, mappings: Mapping[str, int]) -> None:
        if not mappings:
            raise ConfigurationError("Configure the demo customer identity mapping")
        try:
            entries: list[tuple[bytes, CustomerIdentity]] = []
            for token, customer_id in mappings.items():
                if not _TOKEN.fullmatch(token):
                    raise ValueError("Invalid demo token shape")
                entries.append(
                    (
                        hashlib.sha256(token.encode("ascii")).digest(),
                        CustomerIdentity(customer_id=customer_id),
                    )
                )
            self._entries = tuple(entries)
        except (ValidationError, ValueError, TypeError) as exc:
            raise ConfigurationError("Invalid demo customer identity mapping") from exc

    @classmethod
    def from_environment(cls) -> "DemoIdentityResolver":
        try:
            value = json.loads(
                os.environ.get("DEMO_CUSTOMER_TOKENS_JSON", ""),
                object_pairs_hook=_unique_object,
            )
            if not isinstance(value, dict):
                raise ValueError("Expected token-to-customer mapping")
            return cls(value)
        except (ValueError, TypeError) as exc:
            raise ConfigurationError(
                "Configure a valid demo customer identity mapping"
            ) from exc

    def resolve(self, credential: str | None) -> CustomerIdentity:
        if credential is None or not _TOKEN.fullmatch(credential):
            raise AuthenticationError("Customer identity required")
        digest = hashlib.sha256(credential.encode("ascii")).digest()
        identity = None
        for expected, candidate in self._entries:
            if hmac.compare_digest(digest, expected):
                identity = candidate
        if identity is None:
            raise AuthenticationError("Customer identity required")
        return identity
