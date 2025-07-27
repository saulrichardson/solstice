"""LLM client using the OpenAI Responses API.

This module provides a client for the OpenAI Responses API, which is the new
API that OpenAI is moving towards. It supports both text and multimodal inputs
including images.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Sequence, Union

from src.gateway.app.openai_client import get_async_openai_client

logger = logging.getLogger(__name__)

# Get the centralized client instance
_CLIENT = get_async_openai_client()


async def _call_llm_async(
    *,
    system_prompt: str,
    user_content: str | Sequence[dict[str, str]],
    model: str = "gpt-4.1",  # Use the new gpt-4.1 model from Responses API
    temperature: float = 0.2,
    max_tokens: int | None = None,
) -> str:
    """Send a prompt through the Responses API and return the text output."""
    
    logger.debug("Dispatching Responses API request to model: %s", model)
    
    # Use the responses.create method with correct parameters
    response = await _CLIENT.responses.create(
        model=model,
        instructions=system_prompt,  # System prompt goes to instructions
        input=user_content,  # User content goes to input
        temperature=temperature,
        max_output_tokens=max_tokens if max_tokens else None
    )
    
    # Extract the output text from the response
    # Based on the test output, the structure is: response.output[0].content[0].text
    if hasattr(response, 'output') and response.output:
        # Get the first output message
        output_msg = response.output[0]
        if hasattr(output_msg, 'content') and output_msg.content:
            # Get the text from the first content item
            content_item = output_msg.content[0]
            if hasattr(content_item, 'text'):
                output_text = content_item.text
            else:
                output_text = str(content_item)
        else:
            output_text = str(output_msg)
    else:
        # Fallback
        output_text = str(response)
    
    logger.debug("LLM usage: %s", response.usage if hasattr(response, 'usage') else 'N/A')
    
    return output_text


def call_llm(
    *,
    system_prompt: str,
    user_content: str | Sequence[dict[str, str]],
    model: str = "gpt-4.1",
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

