"""Simple retry wrapper for provider calls.

The goal is not to implement a fully-featured resilience layer but to ensure
that transient network failures (e.g. 5xx, time-outs) don't immediately bubble
up to the API consumer during tests.  The logic is deliberately kept minimal
and synchronous ‑ we rely on ``asyncio.sleep`` for the back-off.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar, Any

from ..providers.base import Provider, ResponseObject, ResponseRequest

logger = logging.getLogger("gateway.retry")

_T = TypeVar("_T")


class RetryableProvider(Provider):
    """Decorator that retries calls to an underlying *Provider* instance."""

    DEFAULT_ATTEMPTS = 3
    DEFAULT_BACKOFF = 0.5  # seconds (base for exponential back-off)

    def __init__(
        self,
        provider: Provider,
        *,
        attempts: int | None = None,
        backoff: float | None = None,
    ) -> None:
        self._provider = provider
        self._attempts = attempts or self.DEFAULT_ATTEMPTS
        self._backoff = backoff or self.DEFAULT_BACKOFF

    # ------------------------------------------------------------------
    # Helper – retry wrapper for arbitrary async callables
    # ------------------------------------------------------------------

    async def _with_retry(self, fn: Callable[[], Awaitable[_T]]) -> _T:
        last_err: Exception | None = None
        for attempt in range(1, self._attempts + 1):
            try:
                return await fn()
            except Exception as exc:  # noqa: BLE001 – broad except on purpose
                last_err = exc
                logger.warning(
                    "Provider call failed (attempt %s/%s): %s",
                    attempt,
                    self._attempts,
                    exc,
                )
                if attempt < self._attempts:
                    # Exponential back-off: base * 2^(n-1)
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))
        assert last_err is not None  # for mypy – will always be set if we exit
        raise last_err

    # ------------------------------------------------------------------
    # Provider interface implementation delegating to wrapped instance
    # ------------------------------------------------------------------

    async def create_response(self, request: ResponseRequest) -> ResponseObject:  # noqa: D401
        return await self._with_retry(lambda: self._provider.create_response(request))


    async def retrieve_response(self, response_id: str) -> ResponseObject:  # noqa: D401
        return await self._with_retry(lambda: self._provider.retrieve_response(response_id))

    async def delete_response(self, response_id: str) -> dict[str, Any]:  # noqa: D401
        return await self._with_retry(lambda: self._provider.delete_response(response_id))

