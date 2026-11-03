"""Typed results returned by the fixed-manual policy search tool."""

from typing import Literal, NotRequired, TypedDict

PolicyScope = Literal[
    "general", "online_return", "return_contact", "preference_exchange", "defect"
]


class PolicyContact(TypedDict):
    channel: Literal[
        "email", "telephone", "telephone_whatsapp", "primary_remote_whatsapp"
    ]
    value: str
    section: str
    pages: list[int]


class ReturnProcedure(TypedDict):
    review_scope: Literal["full_manual"]
    reviewed_source_sha256: str
    required_documents: Literal["not_specified_in_manual"]
    label_issuance: Literal["not_specified_in_manual"]
    posting_instructions: Literal["not_specified_in_manual"]
    refund_deadline_start: Literal["not_specified_in_manual"]
    returns_specific_contact: Literal["not_identified_in_manual"]
    authoritative_email: Literal["unresolved_in_manual"]
    general_contacts: list[PolicyContact]


class RefundInformation(TypedDict):
    same_payment_method: bool
    deadline_business_days: int
    return_freight_payer: Literal["store"]


class OnlineReturnRule(TypedDict):
    applicability: Literal["online_purchase_remorse"]
    request_deadline_calendar_days_after_receipt: int
    minimum_wait_calendar_days: int
    required_customer_facts: list[str]
    excluded_product_conditions: list[str]
    refund_information: RefundInformation
    procedure: ReturnProcedure


class PolicyExcerpt(TypedDict):
    id: str
    source: str
    section: str
    hierarchy: list[str]
    pages: list[int]
    text: str
    online_return_rule: NotRequired[OnlineReturnRule]
    applicability: NotRequired[str]


class PolicySearchResult(TypedDict):
    status: Literal["evidence_found", "insufficient_evidence"]
    records: list[PolicyExcerpt]
    policy_scope: NotRequired[PolicyScope]
    scope_guidance: NotRequired[list[str]]
