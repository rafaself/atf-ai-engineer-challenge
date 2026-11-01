"""Trusted identity resolution and customer registry boundaries."""

from typing import Protocol

from emporio_music_backend.contracts.identity import CustomerIdentity


class CustomerRepository(Protocol):
    def exists(self, identity: CustomerIdentity) -> bool:
        """Check the current imported customer registry; faults are explicit."""
        ...


class CustomerIdentityResolver(Protocol):
    def resolve(self, credential: str | None) -> CustomerIdentity:
        """Resolve a server-configured identity or raise AuthenticationError.

        A credential is supplied by the transport boundary, never model input.
        No credential is retained in the returned identity or execution context.
        """
        ...
