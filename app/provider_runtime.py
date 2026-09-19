from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class ProviderRateLimiter:
    def __init__(self, requests_per_minute: int = 50) -> None:
        self.interval = 60 / max(requests_per_minute, 1)
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = self.interval - (now - self._last_request)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_request = time.monotonic()


async def with_retries(operation: Callable[[], Awaitable[T]], *, attempts: int = 3, base_delay: float = 0.5) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            await asyncio.sleep(base_delay * (2**attempt))
    assert last_error is not None
    raise last_error
