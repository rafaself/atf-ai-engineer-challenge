"""Typed results returned by the fixed-manual policy search tool."""

from typing import Literal, NotRequired, TypedDict


class OnlineReturnRule(TypedDict):
    request_deadline_calendar_days_after_receipt: int
    minimum_wait_calendar_days: int
    required_customer_facts: list[str]
    excluded_product_conditions: list[str]


class PolicyExcerpt(TypedDict):
    id: str
    source: str
    section: str
    hierarchy: list[str]
    pages: list[int]
    text: str
    online_return_rule: NotRequired[OnlineReturnRule]


class PolicySearchResult(TypedDict):
    status: Literal["evidence_found", "insufficient_evidence"]
    records: list[PolicyExcerpt]
