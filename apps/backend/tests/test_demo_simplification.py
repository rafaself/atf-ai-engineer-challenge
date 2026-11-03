"""Approved prototype scope: basic schema checks and one-time demo disclosure."""

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

from emporio_music_backend import paths
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
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.setattr(paths, "CATALOG_DATABASE_PATH", catalog)
    monkeypatch.setattr(paths, "OPERATIONS_DATABASE_PATH", operational_database)
    prepare_data()
    assert products.search(query) == before_product
    assert orders.list_orders(identity, OrderListQuery()) == before_orders


def test_discounted_products_do_not_append_demo_disclosures() -> None:
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
    model_answer = (
        "Instrument 1: R$ 10,00, desconto de 10%, final R$ 9,00.\n"
        "Instrument 2: R$ 10,00, desconto de 10%, final R$ 9,00."
    )
    answer = customer_answer(context, model_answer)
    assert answer.startswith(model_answer)
    assert answer.count("Instrument 1") == answer.count("Instrument 2") == 1
    assert answer.count("10%") == 2
    assert answer == model_answer


def test_one_prepare_command_is_repeatable_preserves_history_and_needs_no_aws(
    tmp_path: Path,
    project_copy: Path,
) -> None:
    data = project_copy / "data"
    catalog, operations, conversations = (
        data / (name + ".sqlite3")
        for name in ("catalog", "operations", "conversations")
    )
    conversations.write_bytes(b"untouched history sentinel")
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    environment["PYTHONPATH"] = str(project_copy / "apps/backend/src")
    # Superseded environment settings must not redirect writes, even outside the project.
    environment.update(
        DATABASE_PATH=str(tmp_path / "wrong-catalog.sqlite3"),
        OPERATIONS_DATABASE_PATH=str(tmp_path / "wrong-operations.sqlite3"),
        CONVERSATION_DATABASE_PATH=str(tmp_path / "wrong-conversations.sqlite3"),
    )
    original = {path: path.read_bytes() for path in data.glob("*.csv")}
    for _ in range(2):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "emporio_music_backend.prepare",
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
    assert not list(tmp_path.glob("wrong-*.sqlite3"))
    assert not (tmp_path / "data").exists()
