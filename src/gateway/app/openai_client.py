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
    """Get the OpenAI API key from central configuration.
    
    This function ensures we always use the API key from our settings,
    not from shell environment variables.
    
    Returns:
        The OpenAI API key
        
    Raises:
        OpenAIClientError: If no API key is configured
    """
    # Force reload settings from .env file only, ignoring shell env vars
    import os
    from dotenv import load_dotenv
    
    # Save current env var
    shell_key = os.environ.get('OPENAI_API_KEY')
    
    # Temporarily remove it
    if shell_key:
        del os.environ['OPENAI_API_KEY']
    
    # Load from .env file
    load_dotenv(override=True)
    env_file_key = os.environ.get('OPENAI_API_KEY')
    
    # Restore shell key (but we won't use it)
    if shell_key:
        os.environ['OPENAI_API_KEY'] = shell_key
    
    if not env_file_key:
        raise OpenAIClientError(
            "OpenAI API key not configured. "
            "Please set OPENAI_API_KEY in your .env file."
        )
    
    # Log first/last few chars for debugging (but not the full key)
    key_preview = f"{env_file_key[:10]}...{env_file_key[-4:]}"
    logger.debug(f"Using OpenAI API key from .env: {key_preview}")
    
    return env_file_key


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