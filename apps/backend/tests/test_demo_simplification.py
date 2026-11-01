"""Approved prototype scope: basic schema checks and one concise snapshot notice."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic_ai import RunContext
from pydantic_ai.messages import ModelRequest, ToolReturnPart
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

from emporio_music_backend.agent.output import customer_answer
from emporio_music_backend.contracts.catalog import ProductSearchQuery
from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.contracts.identity import CustomerIdentity
from emporio_music_backend.contracts.orders import OrderListQuery
from emporio_music_backend.infrastructure.sqlite_orders import SQLiteOrderRepository
from emporio_music_backend.infrastructure.sqlite_repository import (
    SQLiteProductRepository,
)
from emporio_music_backend.prepare import prepare_data


def test_readers_accept_additional_columns_without_exact_ddl_auditing(
    operational_database: Path,
) -> None:
    catalog = operational_database.parent / "operational-catalog.sqlite3"
    products = SQLiteProductRepository(catalog)
    orders = SQLiteOrderRepository(operational_database)
    query = ProductSearchQuery(product_name="GD20")
    identity = CustomerIdentity(customer_id=1)
    before_product = products.search(query)
    before_orders = orders.list_orders(identity, OrderListQuery())
    for database in (catalog, operational_database):
        with sqlite3.connect(database) as connection:
            connection.execute("ALTER TABLE products ADD COLUMN demo_label TEXT")
    assert products.search(query) == before_product
    assert orders.list_orders(identity, OrderListQuery()) == before_orders
    data = Path(__file__).parents[3] / "data"
    prepare_data(
        data,
        catalog,
        operational_database,
        conversations=operational_database.parent / "untouched.sqlite3",
    )
    assert products.search(query) == before_product
    assert orders.list_orders(identity, OrderListQuery()) == before_orders


def test_multiple_discounted_products_share_one_snapshot_notice() -> None:
    products = [
        {
            "product_id": n,
            "name": f"Instrument {n}",
            "price_brl": "10.00",
            "pricing": {
                "payment_method": "standard",
                "discount_kind": "promotion",
                "discount_percent": 10,
                "final_price_brl": "9.00",
            },
        }
        for n in (1, 2)
    ]
    context = RunContext(
        deps=ExecutionContext(),
        model=TestModel(),
        usage=RunUsage(),
        run_id="current",
        messages=[
            ModelRequest(
                parts=[
                    ToolReturnPart("search_available_products", {"products": products})
                ],
                run_id="current",
            )
        ],
    )
    answer = customer_answer(context, "Veja as opções.")
    assert "Instrument 1" in answer and "Instrument 2" in answer
    assert answer.count("10%") == 2
    assert answer.count("fotografia importada") == 1


def test_one_prepare_command_is_repeatable_preserves_history_and_needs_no_aws(
    tmp_path: Path,
) -> None:
    data = Path(__file__).parents[3] / "data"
    catalog, operations, conversations = (
        tmp_path / (name + ".sqlite3")
        for name in ("catalog", "operations", "conversations")
    )
    # Setup has no reason to open the existing history file at all.
    conversations.write_bytes(b"untouched history sentinel")
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    environment.update(
        DATABASE_PATH=str(catalog),
        OPERATIONS_DATABASE_PATH=str(operations),
        CONVERSATION_DATABASE_PATH=str(conversations),
    )
    original = {path: path.read_bytes() for path in data.glob("*.csv")}
    for _ in range(2):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "emporio_music_backend.prepare",
                "--data-dir",
                str(data),
            ],
            env=environment,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert (
            "65 products, 25 promotions, 50 customers, 20 orders and 22 items"
            in result.stdout
        )
    assert conversations.read_bytes() == b"untouched history sentinel"
    assert all(path.read_bytes() == raw for path, raw in original.items())
    with sqlite3.connect(operations) as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='metadata'"
            ).fetchone()
            is None
        )
    with pytest.raises(ValueError, match="separate"):
        prepare_data(data, catalog, catalog, conversations=conversations)
    with pytest.raises(ValueError, match="separate"):
        prepare_data(data, data / "orders.csv", operations, conversations=conversations)
    assert all(path.read_bytes() == raw for path, raw in original.items())
