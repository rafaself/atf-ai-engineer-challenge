"""The policy search dependency used by the agent's policy tool."""

from typing import Protocol

from emporio_music.domain.policies import PolicySearchResult


class PolicySearchPort(Protocol):
    def search(self, query: str) -> PolicySearchResult: ...
