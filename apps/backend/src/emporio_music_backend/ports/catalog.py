"""Read-only product search boundary."""

from typing import Protocol

from emporio_music_backend.contracts.catalog import (
    ProductSearchQuery,
    ProductSearchResult,
)


class ProductRepository(Protocol):
    def search(self, query: ProductSearchQuery) -> ProductSearchResult:
        """Return bounded ordered matches and the total before limiting.

        Apply category/name filters together, inclusive payable-price bounds, and
        active/positive-stock availability when requested. Unknown categories
        and unmatched names return an empty result; multiple matches are kept.
        Raise ProductRetrievalError for operational failures rather than
        substituting an empty result.
        """
        ...
