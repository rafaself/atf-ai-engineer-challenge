"""Prepare the local demo's two source snapshots without touching chat history."""

import argparse
import os
import sys
from pathlib import Path

from emporio_music_backend.infrastructure.catalog_import import (
    CatalogImportError,
    ImportReport,
    import_catalog,
)
from emporio_music_backend.infrastructure.operations_import import (
    OperationsImportError,
    OperationsImportReport,
    import_operations,
)


def prepare_data(
    data_directory: Path,
    catalog: Path,
    operations: Path,
    *,
    conversations: Path,
) -> tuple[ImportReport, OperationsImportReport]:
    sources = [
        data_directory / (name + ".csv")
        for name in (
            "products",
            "categories",
            "promotions",
            "customers",
            "orders",
            "order_items",
        )
    ]
    paths = [catalog, operations, conversations]
    for index, path in enumerate(paths):
        for other in [*paths[index + 1 :], *sources]:
            if path.resolve() == other.resolve() or (
                path.exists() and other.exists() and path.samefile(other)
            ):
                raise ValueError("Source and database paths must be separate")
    product_report = import_catalog(sources[0], sources[1], sources[2], catalog)
    order_report = import_operations(
        sources[3], sources[4], sources[5], catalog, operations
    )
    return product_report, order_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the supplied demo data; preserve chat history"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    try:
        products, orders = prepare_data(
            args.data_dir,
            Path(os.environ.get("DATABASE_PATH", "data/catalog.sqlite3")),
            Path(os.environ.get("OPERATIONS_DATABASE_PATH", "data/operations.sqlite3")),
            conversations=Path(
                os.environ.get(
                    "CONVERSATION_DATABASE_PATH", "data/conversations.sqlite3"
                )
            ),
        )
    except (CatalogImportError, OperationsImportError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Prepared {products.products} products, {products.promotions} promotions, {orders.customers} customers, {orders.orders} orders and {orders.items} items."
    )
    print("Chat history was preserved. Start the API using the README command.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
