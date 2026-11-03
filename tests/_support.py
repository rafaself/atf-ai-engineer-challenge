"""Small helpers for adapting synchronous pytest cases to async APIs."""

import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_async[T](awaitable: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(awaitable)
