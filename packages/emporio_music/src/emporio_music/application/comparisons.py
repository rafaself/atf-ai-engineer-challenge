"""Pure numeric comparisons over identified products in one catalog snapshot."""

from emporio_music.domain.catalog import ProductBatchLookupResult
from emporio_music.domain.comparisons import (
    ComparisonEntry,
    NumericComparison,
    ProductComparisonRequest,
    ProductComparisonResult,
)


def compare_products(
    request: ProductComparisonRequest,
    lookup: ProductBatchLookupResult,
) -> ProductComparisonResult:
    request = ProductComparisonRequest.model_validate(request)
    lookup = ProductBatchLookupResult.model_validate(lookup)
    if lookup.requested_product_ids != request.product_ids:
        raise ValueError("Catalog lookup must match comparison product IDs")
    if lookup.missing_product_ids:
        return ProductComparisonResult(
            status="missing_products",
            payment_method=request.payment_method,
            requested_product_ids=request.product_ids,
            missing_product_ids=lookup.missing_product_ids,
        )

    comparisons: list[NumericComparison] = []
    for field in request.fields:
        entries: list[ComparisonEntry] = []
        for product in lookup.products:
            value = {
                "original_price": product.price_centavos,
                "payable_price": product.pricing.final_price_centavos,
                "stock_quantity": product.stock_quantity,
            }[field]
            entries.append(
                ComparisonEntry(
                    product_id=product.product_id,
                    product_name=product.name,
                    field=field,
                    value=value,
                )
            )
        entries.sort(key=lambda entry: (entry.value, entry.product_id))
        minimum = entries[0].value
        maximum = entries[-1].value
        comparisons.append(
            NumericComparison(
                field=field,
                ascending=tuple(entries),
                minimum_product_ids=tuple(
                    entry.product_id for entry in entries if entry.value == minimum
                ),
                maximum_product_ids=tuple(
                    entry.product_id for entry in entries if entry.value == maximum
                ),
                difference=maximum - minimum,
            )
        )

    return ProductComparisonResult(
        status="complete",
        payment_method=request.payment_method,
        requested_product_ids=request.product_ids,
        comparisons=tuple(comparisons),
    )
