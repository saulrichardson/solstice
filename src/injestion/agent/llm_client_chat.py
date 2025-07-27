"""Modified LLM client to use Chat Completions API instead of Responses API"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Sequence

from src.gateway.app.openai_client import get_async_openai_client

logger = logging.getLogger(__name__)

# Get the centralized client instance
_CLIENT = get_async_openai_client()


async def _call_llm_async(
    *,
    system_prompt: str,
    user_content: str | Sequence[dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """Send a prompt through Chat Completions API and return the text output."""
    
    # Build messages
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Handle user content - can be string or list of content blocks
    if isinstance(user_content, str):
        messages.append({"role": "user", "content": user_content})
    else:
        # For vision, we need to format content blocks properly
        content_blocks = []
        for block in user_content:
            if block["type"] == "text":
                content_blocks.append({"type": "text", "text": block["text"]})
            elif block["type"] == "image_url":
                content_blocks.append({
                    "type": "image_url",
                    "image_url": {
                        "url": block["url"],
                        "detail": block.get("detail", "low")
                    }
                })
        messages.append({"role": "user", "content": content_blocks})
    
    logger.debug("Dispatching Chat Completions request to model: %s", model)
    
    response = await _CLIENT.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"}  # Ensure JSON response
    )
    
    content = response.choices[0].message.content
    logger.debug("LLM usage: %s", response.usage)
    return content


def call_llm(
    *,
    system_prompt: str,
    user_content: str | Sequence[dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """Synchronous wrapper around _call_llm_async."""
    
    return asyncio.run(
        _call_llm_async(
            system_prompt=system_prompt,
            user_content=user_content,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )