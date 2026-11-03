"""Pure policy deadline calculations with explicit missing-evidence outcomes."""

from datetime import date, timedelta

from emporio_music.domain.deadlines import (
    DeadlineRequest,
    DeadlineResult,
    DeadlineStatus,
    RequestStatus,
)
from emporio_music.domain.orders import OrderDetail

_DELIVERY_WINDOWS: dict[str, tuple[int, int, str]] = {
    "campo_grande_metro": (1, 3, "policy-v2.1-s5.1"),
    "pac": (5, 12, "policy-v2.1-s5.2"),
    "sedex": (2, 5, "policy-v2.1-s5.2"),
    "jadlog": (3, 8, "policy-v2.1-s5.2"),
}


def add_business_days(start: date, count: int) -> date:
    """Add weekdays after the reference date; no holiday calendar is modeled."""
    result = start
    weekdays_added = 0
    while weekdays_added < count:
        result += timedelta(days=1)
        if result.weekday() < 5:
            weekdays_added += 1
    return result


def _eligibility_status(
    reference_date: date, deadline: date, request_date: date | None
) -> RequestStatus:
    if request_date is None:
        return "not_checked"
    if request_date < reference_date:
        return "request_before_reference"
    if request_date <= deadline:
        return "within_window"
    return "outside_window"


def _missing(
    request: DeadlineRequest,
    status: DeadlineStatus,
    note: str,
    *,
    source: str,
) -> DeadlineResult:
    return DeadlineResult(
        deadline_type=request.deadline_type,
        status=status,
        order_id=request.order_id,
        policy_source=source,
        note=note,
    )


def calculate_deadline(
    request: DeadlineRequest,
    *,
    order: OrderDetail | None = None,
    order_requested: bool = False,
    customer_selection_required: bool = False,
) -> DeadlineResult:
    """Calculate only deadlines whose reference event is supported by evidence."""
    request = DeadlineRequest.model_validate(request)
    if customer_selection_required:
        return _missing(
            request,
            "customer_selection_required",
            "Select a demo customer before looking up an order.",
            source="operational_snapshot",
        )
    if order_requested and order is None:
        return _missing(
            request,
            "order_not_found",
            "Order was not found in the selected account.",
            source="operational_snapshot",
        )

    if request.deadline_type == "delivery":
        if order is not None and order.estimated_delivery is not None:
            return DeadlineResult(
                deadline_type="delivery",
                status="estimated",
                deadline_start_date=order.estimated_delivery,
                deadline_end_date=order.estimated_delivery,
                order_id=order.order_id,
                policy_source="operational_snapshot.estimated_delivery",
                calendar_basis="stored_estimate",
                note=(
                    "This is the stored estimated delivery date. It does not confirm "
                    "dispatch or actual receipt."
                ),
            )
        if request.reference_date is None:
            return _missing(
                request,
                "missing_reference_date",
                "A dispatch date is needed; purchase and estimated-delivery dates are not substitutes.",
                source="policy-v2.1-s5",
            )
        if request.destination is None:
            return _missing(
                request,
                "missing_destination",
                "Choose the Campo Grande metropolitan area or a supported national service.",
                source="policy-v2.1-s5",
            )
        if request.destination == "other_city" and request.delivery_service is None:
            return _missing(
                request,
                "missing_service",
                "Choose PAC, SEDEX or Jadlog to use the published delivery window.",
                source="policy-v2.1-s5.2",
            )
        service_key = (
            "campo_grande_metro"
            if request.destination == "campo_grande_metro"
            else request.delivery_service
        )
        if service_key is None:
            raise AssertionError("Validated national delivery requires a service")
        minimum, maximum, source = _DELIVERY_WINDOWS[service_key]
        return DeadlineResult(
            deadline_type="delivery",
            status="estimated",
            deadline_start_date=add_business_days(request.reference_date, minimum),
            deadline_end_date=add_business_days(request.reference_date, maximum),
            reference_event="dispatch",
            duration_min_days=minimum,
            duration_max_days=maximum,
            day_count="business",
            calendar_basis="weekends_only_holidays_unmodeled",
            order_id=order.order_id if order is not None else request.order_id,
            policy_source=source,
            note=(
                "This is a policy estimate after the supplied dispatch date, excluding "
                "weekends but not public holidays; it is not a carrier confirmation."
            ),
        )

    if request.deadline_type == "refund":
        return DeadlineResult(
            deadline_type="refund",
            status="policy_reference_unspecified",
            duration_max_days=10,
            day_count="business",
            calendar_basis="weekends_only_holidays_unmodeled",
            order_id=order.order_id if order is not None else request.order_id,
            policy_source="policy-v2.1-s4.1",
            note=(
                "The manual allows up to 10 business days for the refund but does not "
                "state which event starts that clock, so no due date is calculated. "
                "Public holidays are not modeled."
            ),
        )

    if request.deadline_type == "defect_exchange":
        reference_date = (
            order.order_date if order is not None else request.reference_date
        )
        if reference_date is None:
            return _missing(
                request,
                "missing_reference_date",
                "The purchase date is needed to calculate the 30-day defect-exchange window.",
                source="policy-v2.1-s4.2",
            )
        deadline = reference_date + timedelta(days=30)
        return DeadlineResult(
            deadline_type="defect_exchange",
            status="calculated",
            deadline_start_date=reference_date,
            deadline_end_date=deadline,
            reference_event="purchase",
            duration_min_days=30,
            duration_max_days=30,
            day_count="calendar",
            calendar_basis="calendar_days",
            request_status=_eligibility_status(
                reference_date, deadline, request.request_date
            ),
            order_id=order.order_id if order is not None else request.order_id,
            policy_source="policy-v2.1-s4.2",
            note="The policy states 30 calendar days from purchase for a manufacturing defect.",
        )

    if request.deadline_type == "online_return":
        if request.reference_date is None:
            return _missing(
                request,
                "missing_reference_date",
                "The actual receipt date is required; an estimated delivery date is not actual receipt.",
                source="policy-v2.1-s4.1",
            )
        deadline = request.reference_date + timedelta(days=7)
        return DeadlineResult(
            deadline_type="online_return",
            status="calculated",
            deadline_start_date=request.reference_date,
            deadline_end_date=deadline,
            reference_event="actual_receipt",
            duration_min_days=7,
            duration_max_days=7,
            day_count="calendar",
            calendar_basis="calendar_days",
            request_status=_eligibility_status(
                request.reference_date, deadline, request.request_date
            ),
            actual_receipt_date_source="customer_reported",
            order_id=order.order_id if order is not None else request.order_id,
            policy_source="policy-v2.1-s4.1",
            note=(
                "The seven-day online-return window uses the supplied customer-reported "
                "actual receipt date. Order estimates do not establish receipt."
            ),
        )

    if request.deadline_type == "warranty":
        if request.reference_date is None:
            return _missing(
                request,
                "missing_reference_date",
                "The actual receipt date is required for the 90-day legal warranty; an estimated delivery date is not actual receipt.",
                source="policy-v2.1-s8.1",
            )
        deadline = request.reference_date + timedelta(days=90)
        return DeadlineResult(
            deadline_type="warranty",
            status="calculated",
            deadline_start_date=request.reference_date,
            deadline_end_date=deadline,
            reference_event="actual_receipt",
            duration_min_days=90,
            duration_max_days=90,
            day_count="calendar",
            calendar_basis="calendar_days",
            request_status=_eligibility_status(
                request.reference_date, deadline, request.request_date
            ),
            actual_receipt_date_source="customer_reported",
            order_id=order.order_id if order is not None else request.order_id,
            policy_source="policy-v2.1-s8.1",
            note=(
                "This calculates the 90-day legal warranty from customer-reported actual "
                "receipt. Manufacturer warranty needs the product certificate."
            ),
        )

    raise AssertionError("Validated deadline type was not handled")
