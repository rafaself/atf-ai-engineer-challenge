"""Typed inputs and qualified results for policy-based deadline estimates."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from emporio_music.domain.base import ContractModel, NonblankText
from emporio_music.domain.orders import DatabaseId

DeadlineType = Literal[
    "delivery", "online_return", "defect_exchange", "refund", "warranty"
]
DeadlineEvent = Literal["purchase", "dispatch", "actual_receipt"]
DeliveryDestination = Literal["campo_grande_metro", "other_city"]
DeliveryService = Literal["pac", "sedex", "jadlog"]
DeadlineStatus = Literal[
    "calculated",
    "estimated",
    "missing_reference_date",
    "missing_destination",
    "missing_service",
    "order_not_found",
    "policy_reference_unspecified",
]
RequestStatus = Literal[
    "within_window", "outside_window", "request_before_reference", "not_checked"
]


class DeadlineRequest(ContractModel):
    deadline_type: DeadlineType
    order_id: DatabaseId | None = None
    reference_date: date | None = None
    reference_event: DeadlineEvent | None = None
    request_date: date | None = None
    destination: DeliveryDestination | None = None
    delivery_service: DeliveryService | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> Self:
        if (self.reference_date is None) != (self.reference_event is None):
            raise ValueError("reference date and event must be provided together")
        expected_event: dict[str, DeadlineEvent] = {
            "delivery": "dispatch",
            "online_return": "actual_receipt",
            "defect_exchange": "purchase",
            "warranty": "actual_receipt",
        }
        expected = expected_event.get(self.deadline_type)
        if expected is None and self.reference_event is not None:
            raise ValueError("refund deadline start is not defined by policy")
        if expected is not None and self.reference_event not in {None, expected}:
            raise ValueError("reference event does not match the requested deadline")
        if self.request_date is not None and self.deadline_type not in {
            "online_return",
            "defect_exchange",
            "warranty",
        }:
            raise ValueError("request date only applies to an eligibility window")
        if self.deadline_type != "delivery" and (
            self.destination is not None or self.delivery_service is not None
        ):
            raise ValueError("delivery details only apply to a delivery deadline")
        if self.delivery_service is not None and self.destination != "other_city":
            raise ValueError("a national delivery service requires other_city")
        return self


class DeadlineResult(ContractModel):
    deadline_type: DeadlineType
    status: DeadlineStatus
    deadline_start_date: date | None = None
    deadline_end_date: date | None = None
    reference_event: DeadlineEvent | None = None
    duration_min_days: Annotated[int, Field(strict=True, ge=0, le=3650)] | None = None
    duration_max_days: Annotated[int, Field(strict=True, ge=0, le=3650)] | None = None
    day_count: Literal["calendar", "business"] | None = None
    calendar_basis: (
        Literal["calendar_days", "weekends_only_holidays_unmodeled", "stored_estimate"]
        | None
    ) = None
    request_status: RequestStatus = "not_checked"
    actual_receipt_date_source: Literal[
        "customer_reported", "not_available", "not_applicable"
    ] = "not_applicable"
    order_id: DatabaseId | None = None
    policy_source: NonblankText
    note: NonblankText
