"""Small exact-price rule; source prices and promotion records are never rewritten."""

from emporio_music_backend.contracts.pricing import (
    PaymentMethod,
    ProductPricing,
    PromotionOffer,
)


def calculate_pricing(
    price_centavos: int,
    *,
    available: bool,
    payment_method: PaymentMethod,
    promotion: PromotionOffer | None = None,
) -> ProductPricing:
    if type(price_centavos) is not int or not 0 < price_centavos <= 2**63 - 1:
        raise ValueError("Expected a supported original catalog price")
    if payment_method not in {"standard", "pix"}:
        raise ValueError("Unsupported payment method")
    kind = "none"
    percent = 0
    applied = None
    if available and promotion is not None:
        applied = PromotionOffer.model_validate(promotion)
        kind, percent = "promotion", applied.discount_percent
    elif available and payment_method == "pix":
        kind, percent = "pix", 5
    return ProductPricing.model_validate(
        {
            "payment_method": payment_method,
            "final_price_centavos": (price_centavos * (100 - percent) + 50) // 100,
            "discount_percent": percent,
            "discount_kind": kind,
            "promotion_id": applied.promotion_id if applied else None,
            "promotion_description": applied.description if applied else None,
        }
    )
