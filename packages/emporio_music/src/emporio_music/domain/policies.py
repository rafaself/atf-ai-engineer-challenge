"""Typed results returned by the fixed-manual policy search tool."""

from typing import Literal, TypedDict


class PolicyExcerpt(TypedDict):
    id: str
    source: str
    section: str
    hierarchy: list[str]
    pages: list[int]
    text: str


class PolicySearchResult(TypedDict):
    status: Literal["evidence_found", "insufficient_evidence"]
    records: list[PolicyExcerpt]
