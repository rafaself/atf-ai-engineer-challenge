"""Small helpers for adapting synchronous pytest cases to async APIs."""

import asyncio
from collections.abc import Coroutine
from typing import Any


def run_async[T](awaitable: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(awaitable)
