"""Centralized OpenAI client management.

This module ensures all OpenAI API usage in the codebase goes through
the central configuration, preventing issues with environment variables
taking precedence over project settings.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from openai import AsyncOpenAI, OpenAI

from .config import settings

logger = logging.getLogger(__name__)


class OpenAIClientError(Exception):
    """Raised when OpenAI client cannot be initialized."""
    pass


@lru_cache(maxsize=1)
def get_openai_api_key() -> str:
    """Return the OpenAI API key prioritising explicit project settings.

    The precedence order is:

    1. `settings.openai_api_key` – value injected via *pydantic-settings* which
       already resolves `.env` files and regular environment variables.
    2. ``OPENAI_API_KEY`` environment variable – fallback so that existing
       shell workflows keep working when the settings object is not used.

    Having a single helper centralises the logic, avoids the need for callers
    to deal with ``Settings`` directly and, crucially, **does not** mutate the
    process environment (the previous implementation deleted / restored
    ``OPENAI_API_KEY`` which created hard-to-debug race-conditions in
    concurrent code and side-effects in unrelated threads).
    """

    # 1. Primary source – project configuration
    if settings.openai_api_key:
        key = settings.openai_api_key
        logger.debug("Using OpenAI API key from Settings")
        return key

    # 2. Fallback – raw environment variable (allows quick experimentation)
    import os

    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        logger.debug("Using OpenAI API key from environment variable")
        return env_key

    # If we reach this point no key is configured ⇒ raise a descriptive error
    raise OpenAIClientError(
        "OpenAI API key not configured. Set it via the OPENAI_API_KEY "
        "environment variable or the .env file recognised by the Settings "
        "object (see src/gateway/app/config.py)."
    )


@lru_cache(maxsize=1)
def get_async_openai_client() -> AsyncOpenAI:
    """Get a singleton AsyncOpenAI client instance.
    
    This ensures all async code uses the same client instance with
    the correct API key from our central configuration.
    
    Returns:
        Configured AsyncOpenAI client
        
    Raises:
        OpenAIClientError: If client cannot be initialized
    """
    api_key = get_openai_api_key()
    client = AsyncOpenAI(
        api_key=api_key,
        # Explicitly set to None to ignore any OPENAI_API_KEY env var
        default_headers={"OpenAI-Beta": "assistants=v2"}
    )
    logger.info("Initialized AsyncOpenAI client")
    return client


@lru_cache(maxsize=1)
def get_sync_openai_client() -> OpenAI:
    """Get a singleton OpenAI client instance for synchronous code.
    
    Returns:
        Configured OpenAI client
        
    Raises:
        OpenAIClientError: If client cannot be initialized
    """
    api_key = get_openai_api_key()
    client = OpenAI(
        api_key=api_key,
        # Explicitly set to None to ignore any OPENAI_API_KEY env var
        default_headers={"OpenAI-Beta": "assistants=v2"}
    )
    logger.info("Initialized OpenAI client")
    return client


def validate_api_key() -> bool:
    """Validate that the API key is properly configured.
    
    Returns:
        True if API key is valid format, False otherwise
    """
    try:
        api_key = get_openai_api_key()
        # Basic validation - OpenAI keys start with 'sk-'
        return api_key.startswith('sk-') and len(api_key) > 20
    except OpenAIClientError:
        return False
