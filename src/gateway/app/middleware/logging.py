"""Request / response logging utilities for the Solstice Gateway.

The gateway only needs **very** light-weight structured logging so we keep the
implementation minimal to avoid introducing additional runtime dependencies.
The middleware assigns a short *request_id* to every incoming HTTP request so
that individual log lines can be correlated when the service is deployed in a
concurrent environment.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("gateway")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Attach a short *request_id* and log basic request / response metadata."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:  # noqa: D401  (simple dispatch signature)
        # Generate a concise request identifier – we don't need cryptographic
        # randomness, only uniqueness for the lifetime of the process.
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id

        started = time.time()
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.time() - started) * 1_000
            logger.info(
                "[request %s] %s %s → %s (%.1f ms)",
                request_id,
                request.method,
                request.url.path,
                (response.status_code if "response" in locals() else "error"),
                duration_ms,
            )


# ---------------------------------------------------------------------------
# Helper functions used by the main application module
# ---------------------------------------------------------------------------


def log_llm_request(
    request_id: str,
    provider: str,
    model: str,
    payload: dict,
) -> None:
    """Log the outgoing request that will be sent to the provider."""

    logger.debug(
        "[request %s] → %s | model=%s | payload=%s",
        request_id,
        provider,
        model,
        payload,
    )


def log_llm_response(
    request_id: str,
    provider: str,
    model: str,
    response: dict,
    duration: float,
) -> None:
    """Log the response we just received from the provider."""

    logger.debug(
        "[request %s] ← %s | model=%s | %.0f ms | response=%s",
        request_id,
        provider,
        model,
        duration * 1_000,
        response,
    )

