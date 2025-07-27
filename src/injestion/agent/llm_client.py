"""Thin wrapper around the gateway's OpenAI *Responses* provider.

This helper intentionally hides all asynchronous details so call-sites in the
ingestion pipeline can use simple blocking functions.  Under the hood we still
call the provider asynchronously to benefit from non-blocking HTTP I/O.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Sequence

from gateway.app.providers.openai_provider import OpenAIProvider
from gateway.app.providers.base import ResponseObject, ResponseRequest

logger = logging.getLogger(__name__)

# Single provider instance reused across the process.  The constructor will
# raise if the *OPENAI_API_KEY* environment variable is missing – we let that
# propagate because running without credentials is a hard configuration error.
_PROVIDER = OpenAIProvider()


async def _call_llm_async(
    *,
    system_prompt: str,
    user_content: str | Sequence[dict[str, str]],
    model: str = "gpt-4o-mini",  # latest reasoning-optimised model
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """Send a prompt through the gateway and return the text output."""

    request = ResponseRequest(
        model=model,
        instructions=system_prompt,
        input=user_content,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )

    logger.debug("Dispatching LLM request: %s", request.model_dump())
    rsp: ResponseObject = await _PROVIDER.create_response(request)

    if not rsp.output or "text" not in rsp.output[0]:
        raise ValueError("Gateway returned response without text output")

    logger.debug("LLM usage: %s", rsp.usage)
    return rsp.output[0]["text"]  # type: ignore[index]


def call_llm(
    *,
    system_prompt: str,
    user_content: str | Sequence[dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """Synchronous convenience wrapper around :pyfunc:`_call_llm_async`."""

    return asyncio.run(
        _call_llm_async(
            system_prompt=system_prompt,
            user_content=user_content,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )

