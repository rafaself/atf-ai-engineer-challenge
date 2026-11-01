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
    catalog_database_path: Path,
    operations_database_path: Path,
    *,
    conversation_database_path: Path,
) -> tuple[ImportReport, OperationsImportReport]:
    source_paths = [
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
    database_paths = [
        catalog_database_path,
        operations_database_path,
        conversation_database_path,
    ]
    for index, database_path in enumerate(database_paths):
        for other_path in [*database_paths[index + 1 :], *source_paths]:
            if database_path.resolve() == other_path.resolve() or (
                database_path.exists()
                and other_path.exists()
                and database_path.samefile(other_path)
            ):
                raise ValueError("Source and database paths must be separate")
    catalog_import_report = import_catalog(
        source_paths[0], source_paths[1], source_paths[2], catalog_database_path
    )
    operations_import_report = import_operations(
        source_paths[3],
        source_paths[4],
        source_paths[5],
        catalog_database_path,
        operations_database_path,
    )
    return catalog_import_report, operations_import_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the supplied demo data; preserve chat history"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    try:
        catalog_import_report, operations_import_report = prepare_data(
            args.data_dir,
            Path(os.environ.get("DATABASE_PATH", "data/catalog.sqlite3")),
            Path(os.environ.get("OPERATIONS_DATABASE_PATH", "data/operations.sqlite3")),
            conversation_database_path=Path(
                os.environ.get(
                    "CONVERSATION_DATABASE_PATH", "data/conversations.sqlite3"
                )
            ),
        )
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
