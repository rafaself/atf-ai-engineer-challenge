"""Prepare the local demo's two source snapshots without touching chat history."""

import sys

from emporio_music import paths
from emporio_music.infrastructure.catalog_import import (
    CatalogImportError,
    ImportReport,
    import_catalog,
)
from emporio_music.infrastructure.operations_import import (
    OperationsImportError,
    OperationsImportReport,
    import_operations,
)


def prepare_data() -> tuple[ImportReport, OperationsImportReport]:
    catalog_import_report = import_catalog(
        paths.CATALOG_DIRECTORY / "products.csv",
        paths.CATALOG_DIRECTORY / "categories.csv",
        paths.CATALOG_DIRECTORY / "promotions.csv",
        paths.CATALOG_DATABASE_PATH,
    )
    operations_import_report = import_operations(
        paths.OPERATIONS_DIRECTORY / "customers.csv",
        paths.OPERATIONS_DIRECTORY / "orders.csv",
        paths.OPERATIONS_DIRECTORY / "order_items.csv",
        paths.CATALOG_DATABASE_PATH,
        paths.OPERATIONS_DATABASE_PATH,
    )
    return catalog_import_report, operations_import_report


def main() -> int:
    try:
        catalog_import_report, operations_import_report = prepare_data()
    except (CatalogImportError, OperationsImportError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Prepared {catalog_import_report.products} products, "
        f"{catalog_import_report.promotions} promotions, "
        f"{operations_import_report.customers} customers, "
        f"{operations_import_report.orders} orders and "
        f"{operations_import_report.items} items."
    )
    print("Chat history was preserved. Start the API using the README command.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
