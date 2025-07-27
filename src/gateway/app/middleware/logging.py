import json
import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware

_formatter: logging.Formatter = jsonlogger.JsonFormatter()

# Configure logging with the formatter chosen above.
_handler = logging.StreamHandler()
_handler.setFormatter(_formatter)

logger = logging.getLogger("gateway")
# Prevent duplicate handlers in re-loads (e.g., during tests).
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    logger.addHandler(_handler)

logger.setLevel(logging.INFO)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Store request ID for use in other parts of the app
        request.state.request_id = request_id

        # Log request
        request_body = None
        if request.method == "POST":
            body = await request.body()
            request_body = json.loads(body) if body else None

            # Reset body for downstream processing
            async def receive():
                return {"type": "http.request", "body": body}

            request._receive = receive

        logger.info(
            "request_received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "body": request_body,
            },
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


def log_llm_request(request_id: str, provider: str, model: str, request_data: dict):
    """Log LLM API request details."""
    # Calculate request size
    input_data = request_data.get("input", "")
    if isinstance(input_data, str):
        total_chars = len(input_data)
    elif isinstance(input_data, list):
        total_chars = sum(len(str(item)) for item in input_data)
    else:
        total_chars = 0

    logger.info(
        "llm_request",
        extra={
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "has_previous_response_id": bool(request_data.get("previous_response_id")),
            "has_tools": bool(request_data.get("tools")),
            "store": request_data.get("store", True),
            "total_chars": total_chars,
        },
    )


def log_llm_response(
    request_id: str, provider: str, model: str, response: dict, duration: float
):
    """Log LLM API response details."""
    # Extract token usage from response
    input_tokens = response.get("input_tokens", 0)
    output_tokens = response.get("output_tokens", 0)
    reasoning_tokens = response.get("reasoning_tokens", 0)
    total_tokens = response.get("usage", {}).get(
        "total_tokens", input_tokens + output_tokens + reasoning_tokens
    )

    logger.info(
        "llm_response",
        extra={
            "request_id": request_id,
            "provider": provider,
            "model": model,
            "response_id": response.get("id"),
            "duration_ms": round(duration * 1000, 2),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens,
            "has_tool_calls": bool(response.get("tool_calls")),
            "status": response.get("status"),
        },
    )
