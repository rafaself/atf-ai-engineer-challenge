"""Pure quote, installment and supported-threshold calculations."""

from collections.abc import Sequence

from emporio_music.application.pricing import calculate_pricing
from emporio_music.domain.catalog import ProductBatchLookupResult, ProductSummary
from emporio_music.domain.pricing import PaymentMethod, ProductPricing, PromotionOffer
from emporio_music.domain.quotes import (
    InstallmentMinimumRule,
    InstallmentPlan,
    InstallmentTotalScope,
    QuoteCalculationStatus,
    QuoteLine,
    QuoteRequest,
    QuoteResult,
    QuoteTotalScope,
    RequestedInstallmentStatus,
    ShippingQuote,
    SplitPaymentQuote,
)

_MAX_CENTAVOS = 2**63 - 1
_FREIGHT_THRESHOLD = 50_000
_FREIGHT_BELOW_THRESHOLD = 3_500
_MIXED_PAYMENT_THRESHOLD = 200_000


def _checked_product_total(amounts: Sequence[int]) -> int:
    total = sum(amounts)
    if total > _MAX_CENTAVOS:
        raise ValueError("Quote total exceeds the supported centavo range")
    return total


def calculate_installment_options(total_centavos: int) -> tuple[InstallmentPlan, ...]:
    """Return policy-eligible, exact-centavo credit allocations for a total."""
    if type(total_centavos) is not int or not 0 <= total_centavos <= _MAX_CENTAVOS:
        raise ValueError("Installment total must be nonnegative supported centavos")
    if total_centavos == 0:
        return ()

    plans: list[InstallmentPlan] = []
    for count in range(1, 13):
        quotient, remainder = divmod(total_centavos, count)
        amounts = tuple(
            quotient + (1 if index < remainder else 0) for index in range(count)
        )
        if count <= 3:
            if total_centavos < 5_000:
                continue
            minimum_rule: InstallmentMinimumRule = "total_at_least_50"
        elif count <= 6:
            if min(amounts) < 8_000:
                continue
            minimum_rule = "each_at_least_80"
        else:
            if min(amounts) < 10_000:
                continue
            minimum_rule = "each_at_least_100"
        plans.append(
            InstallmentPlan(
                count=count,
                eligibility=(
                    "policy_ambiguous" if min(amounts) < 10_000 else "eligible"
                ),
                amounts_centavos=amounts,
                total_centavos=total_centavos,
                minimum_rule=minimum_rule,
            )
        )
    return tuple(plans)


def _promotion_from_pricing(pricing: ProductPricing) -> PromotionOffer | None:
    if pricing.discount_kind != "promotion":
        return None
    return PromotionOffer.model_validate(
        {
            "promotion_id": pricing.promotion_id,
            "discount_percent": pricing.discount_percent,
            "description": pricing.promotion_description,
        }
    )


def _pricing_for(
    product: ProductSummary, payment_method: PaymentMethod
) -> ProductPricing:
    return calculate_pricing(
        product.price_centavos,
        available=product.available,
        payment_method=payment_method,
        promotion=_promotion_from_pricing(product.pricing),
    )


def _split_quote(
    request: QuoteRequest,
    *,
    original_total: int,
    standard_total: int,
) -> SplitPaymentQuote:
    if request.payment_intent != "split":
        return SplitPaymentQuote()

    original_eligible = original_total > _MIXED_PAYMENT_THRESHOLD
    standard_eligible = standard_total > _MIXED_PAYMENT_THRESHOLD
    if original_eligible != standard_eligible:
        return SplitPaymentQuote(
            status="eligibility_basis_ambiguous",
            policy_source="policy-v2.1-s3.1",
            note=(
                "Mixed payment requires a purchase above R$ 2.000,00, but the policy "
                "does not say whether the threshold uses original or discounted totals."
            ),
        )
    if not standard_eligible:
        return SplitPaymentQuote(
            status="not_eligible_at_threshold",
            policy_source="policy-v2.1-s3.1",
            note="Mixed payment is allowed only above R$ 2.000,00.",
        )
    if request.pix_allocation_centavos is None:
        return SplitPaymentQuote(
            status="allocation_required",
            policy_source="policy-v2.1-s3.1",
            note="Ask which part the customer wants to pay by PIX.",
        )
    pix_amount = request.pix_allocation_centavos
    if not 0 < pix_amount < standard_total:
        return SplitPaymentQuote(
            status="allocation_invalid",
            policy_source="policy-v2.1-s3.1",
            note="A split requires positive PIX and credit amounts.",
        )

    credit_amount = standard_total - pix_amount
    return SplitPaymentQuote(
        status="eligible",
        pix_amount_centavos=pix_amount,
        credit_amount_centavos=credit_amount,
        credit_installment_options=calculate_installment_options(credit_amount),
        pix_discount_applied="policy_ambiguous",
        policy_source="policy-v2.1-s3.1",
        note=(
            "The PIX and credit allocations sum to the standard payable total. "
            "No extra PIX discount is applied because policy does not specify "
            "discount treatment for mixed payment."
        ),
    )


def _shipping_quote(
    request: QuoteRequest,
    *,
    original_total: int,
    selected_total: int,
) -> ShippingQuote:
    if request.destination is None:
        return ShippingQuote(status="not_requested")
    if request.destination == "other_city":
        return ShippingQuote(
            status="unsupported_destination",
            policy_source="policy-v2.1-s5.2",
            note=(
                "National freight needs destination CEP, parcel weight and dimensions; "
                "no charge is estimated. Large instruments may need an individual quote."
            ),
        )

    original_free = original_total >= _FREIGHT_THRESHOLD
    selected_free = selected_total >= _FREIGHT_THRESHOLD
    source = "freight-clarification-v1; policy-v2.1-s5.1"
    if original_free != selected_free:
        return ShippingQuote(
            status="basis_ambiguous",
            policy_source=source,
            note=(
                "The approved rule makes orders at or above R$ 500,00 free, but "
                "does not define whether the threshold uses pre- or post-discount total."
            ),
        )
    charge = 0 if selected_free else _FREIGHT_BELOW_THRESHOLD
    return ShippingQuote(
        status="supported",
        charge_centavos=charge,
        policy_source=source,
        note=(
            "Campo Grande metropolitan freight is free at or above R$ 500,00; "
            "below that threshold it is R$ 35,00. The result is the same using "
            "original and discounted merchandise totals."
        ),
    )


def calculate_quote(
    request: QuoteRequest,
    lookup: ProductBatchLookupResult,
) -> QuoteResult:
    """Quote identified products from one repository snapshot."""
    request = QuoteRequest.model_validate(request)
    lookup = ProductBatchLookupResult.model_validate(lookup)
    item_ids = tuple(item.product_id for item in request.items)
    if lookup.requested_product_ids != item_ids:
        raise ValueError("Catalog lookup must match quote item IDs in request order")

    products = {product.product_id: product for product in lookup.products}
    lines: list[QuoteLine] = []
    unavailable_ids: list[int] = []
    insufficient_stock: list[tuple[int, int, int]] = []
    original_subtotals: list[int] = []
    standard_subtotals: list[int] = []
    pix_subtotals: list[int] = []

    for item in request.items:
        product = products.get(item.product_id)
        if product is None:
            continue
        original_subtotal = product.price_centavos * item.quantity
        if original_subtotal > _MAX_CENTAVOS:
            raise ValueError("Quote line exceeds the supported centavo range")

        if not product.available:
            unavailable_ids.append(product.product_id)
            lines.append(
                QuoteLine(
                    product_id=product.product_id,
                    product_name=product.name,
                    quantity=item.quantity,
                    stock_quantity=product.stock_quantity,
                    status="unavailable",
                    original_unit_centavos=product.price_centavos,
                    standard_pricing=product.pricing,
                    pix_pricing=_pricing_for(product, "pix"),
                    original_subtotal_centavos=original_subtotal,
                )
            )
            continue
        if item.quantity > product.stock_quantity:
            insufficient_stock.append(
                (product.product_id, item.quantity, product.stock_quantity)
            )
            lines.append(
                QuoteLine(
                    product_id=product.product_id,
                    product_name=product.name,
                    quantity=item.quantity,
                    stock_quantity=product.stock_quantity,
                    status="insufficient_stock",
                    original_unit_centavos=product.price_centavos,
                    original_subtotal_centavos=original_subtotal,
                )
            )
            continue

        standard = product.pricing
        if standard.payment_method != "standard":
            raise ValueError("Batch quote lookup must use standard pricing")
        pix = _pricing_for(product, "pix")
        standard_subtotal = standard.final_price_centavos * item.quantity
        pix_subtotal = pix.final_price_centavos * item.quantity
        for amount in (standard_subtotal, pix_subtotal):
            if amount > _MAX_CENTAVOS:
                raise ValueError("Quote line exceeds the supported centavo range")
        original_subtotals.append(original_subtotal)
        standard_subtotals.append(standard_subtotal)
        pix_subtotals.append(pix_subtotal)
        lines.append(
            QuoteLine(
                product_id=product.product_id,
                product_name=product.name,
                quantity=item.quantity,
                stock_quantity=product.stock_quantity,
                status="quoted",
                original_unit_centavos=product.price_centavos,
                standard_pricing=standard,
                pix_pricing=pix,
                original_subtotal_centavos=original_subtotal,
                standard_subtotal_centavos=standard_subtotal,
                pix_subtotal_centavos=pix_subtotal,
            )
        )

    calculation_status: QuoteCalculationStatus = "complete"
    if lookup.missing_product_ids:
        calculation_status = "missing_products"
    elif unavailable_ids or insufficient_stock:
        calculation_status = "unavailable_products"
    complete = calculation_status == "complete"

    if not complete:
        return QuoteResult(
            payment_intent=request.payment_intent,
            calculation_status=calculation_status,
            lines=tuple(lines),
            missing_product_ids=lookup.missing_product_ids,
            unavailable_product_ids=tuple(unavailable_ids),
            insufficient_stock=tuple(insufficient_stock),
            quoted_total_scope="not_calculated",
            installment_total_scope="not_calculated",
            requested_installments=request.requested_installments,
            requested_installment_status=(
                "not_calculated"
                if request.requested_installments is not None
                else "not_requested"
            ),
            split_payment=SplitPaymentQuote(
                status=(
                    "not_calculated"
                    if request.payment_intent == "split"
                    else "not_requested"
                )
            ),
            shipping=ShippingQuote(
                status="not_calculated" if request.destination else "not_requested"
            ),
        )

    original_total = _checked_product_total(original_subtotals)
    standard_total = _checked_product_total(standard_subtotals)
    pix_total = _checked_product_total(pix_subtotals)
    selected_merchandise_total = {
        "compare": None,
        "pix": pix_total,
        "credit": standard_total,
        "split": standard_total,
    }[request.payment_intent]
    split = _split_quote(
        request, original_total=original_total, standard_total=standard_total
    )

    shipping = _shipping_quote(
        request,
        original_total=original_total,
        selected_total=(
            selected_merchandise_total
            if selected_merchandise_total is not None
            else standard_total
        ),
    )
    quoted_total_scope: QuoteTotalScope
    if request.payment_intent == "compare":
        quoted_total = None
        quoted_total_scope = "comparison_only"
    elif request.destination is None:
        quoted_total = selected_merchandise_total
        quoted_total_scope = "merchandise_only"
    elif shipping.status == "supported":
        assert selected_merchandise_total is not None
        assert shipping.charge_centavos is not None
        quoted_total = selected_merchandise_total + shipping.charge_centavos
        if quoted_total > _MAX_CENTAVOS:
            raise ValueError("Quote total exceeds the supported centavo range")
        quoted_total_scope = "includes_supported_shipping"
    else:
        quoted_total = None
        quoted_total_scope = "shipping_unresolved"

    installment_options: tuple[InstallmentPlan, ...]
    requested_options: tuple[InstallmentPlan, ...]
    installment_total_scope: InstallmentTotalScope
    if request.payment_intent == "split":
        installment_total = (
            split.credit_amount_centavos if split.status == "eligible" else None
        )
        installment_options = ()
        requested_options = split.credit_installment_options
        installment_total_scope = "not_applicable"
    elif request.payment_intent in {"credit", "compare"}:
        installment_total = (
            quoted_total
            if quoted_total is not None
            else standard_total
            if request.payment_intent == "compare"
            else selected_merchandise_total
        )
        installment_options = (
            calculate_installment_options(installment_total)
            if installment_total is not None
            else ()
        )
        requested_options = installment_options
        installment_total_scope = (
            "includes_supported_shipping"
            if request.destination is not None and shipping.status == "supported"
            else "merchandise_only"
        )
    else:
        installment_total = None
        installment_options = ()
        requested_options = ()
        installment_total_scope = "not_applicable"
    requested_status: RequestedInstallmentStatus = "not_requested"
    if request.requested_installments is not None:
        if installment_total is None:
            requested_status = "not_calculated"
        else:
            requested_plans = tuple(
                plan
                for plan in requested_options
                if plan.count == request.requested_installments
            )
            if any(plan.eligibility == "eligible" for plan in requested_plans):
                requested_status = "eligible"
            elif requested_plans:
                requested_status = "policy_ambiguous"
            else:
                requested_status = "below_minimum"

    notes: tuple[str, ...] = (
        "Policy section 3.1 permits some installments below R$ 100,00, while section 3 states a general R$ 100,00 minimum. Affected plans are marked policy_ambiguous rather than treated as confirmed.",
    )
    if request.destination is not None and shipping.status != "supported":
        notes += (
            "Installment amounts use the known merchandise total only; unresolved shipping is excluded.",
        )
    if request.payment_intent == "split":
        notes += (
            "Mixed payment is eligible only when both original and standard payable merchandise totals are above R$ 2.000,00; policy does not identify which total controls.",
        )

    return QuoteResult(
        payment_intent=request.payment_intent,
        calculation_status="complete",
        lines=tuple(lines),
        original_total_centavos=original_total,
        standard_total_centavos=standard_total,
        pix_total_centavos=pix_total,
        selected_merchandise_total_centavos=selected_merchandise_total,
        quoted_total_centavos=quoted_total,
        quoted_total_scope=quoted_total_scope,
        selected_installment_options=installment_options,
        installment_total_scope=installment_total_scope,
        max_installments=max(
            (
                plan.count
                for plan in requested_options
                if plan.eligibility == "eligible"
            ),
            default=None,
        ),
        uncertain_max_installments=max(
            (
                plan.count
                for plan in requested_options
                if plan.eligibility == "policy_ambiguous"
            ),
            default=None,
        ),
        requested_installments=request.requested_installments,
        requested_installment_status=requested_status,
        split_payment=split,
        shipping=shipping,
        policy_notes=notes,
        installment_policy_source="policy-v2.1-s3.1",
    )
