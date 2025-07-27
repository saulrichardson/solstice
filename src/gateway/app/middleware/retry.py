import logging
from collections.abc import Callable
from typing import TypeVar

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("gateway.retry")

T = TypeVar("T")

# Define retryable exceptions
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
)


def with_retry(
    max_attempts: int = 3, min_wait: float = 1, max_wait: float = 10
) -> Callable:
    """
    Decorator for adding retry logic to async functions.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class RetryableProvider:
    """Wrapper for providers that adds retry logic."""

    def __init__(self, provider, max_attempts=3):
        self.provider = provider
        self.max_attempts = max_attempts

        # Wrap the provider methods with retry logic
        self.create_response = with_retry(max_attempts=max_attempts)(
            self._create_response_with_logging
        )
        self.stream_response = with_retry(max_attempts=max_attempts)(
            self.provider.stream_response
        )
        self.retrieve_response = with_retry(max_attempts=max_attempts)(
            self.provider.retrieve_response
        )
        self.delete_response = with_retry(max_attempts=max_attempts)(
            self.provider.delete_response
        )

    async def _create_response_with_logging(self, request):
        """Wrapper that adds logging to retries."""
        try:
            return await self.provider.create_response(request)
        except Exception as e:
            logger.warning(f"Provider error: {type(e).__name__}: {e!s}")
            raise
