"""Centralized configuration management for Solstice.

This module provides a single source of truth for all environment-based
configuration across the Solstice codebase. It uses pydantic-settings to:
- Load configuration from .env files
- Validate types and values
- Provide defaults where appropriate
- Support environment variable overrides
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field, computed_field


class Settings(BaseSettings):
    """Global settings for Solstice applications."""
    
    # Gateway Configuration
    solstice_gateway_url: str | None = Field(
        None, 
        description="Full gateway URL (overrides host/port if set)"
    )
    solstice_gateway_host: str = Field(
        "localhost",
        description="Gateway hostname"
    )
    solstice_gateway_port: int = Field(
        8000,
        description="Gateway port number"
    )
    
    # API Keys
    openai_api_key: str | None = Field(
        None,
        description="OpenAI API key for LLM calls"
    )
    
    # Logging
    solstice_log_level: str = Field(
        "INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # Cache Configuration
    filesystem_cache_dir: str = Field(
        "data/cache",
        description="Base directory for filesystem cache"
    )
    
    @computed_field
    @property
    def gateway_url(self) -> str:
        """Compute the full gateway URL from components."""
        if self.solstice_gateway_url:
            return self.solstice_gateway_url.rstrip("/")
        return f"http://{self.solstice_gateway_host}:{self.solstice_gateway_port}"
    
    model_config = {
        # Look for .env file in project root (3 levels up from this file)
        "env_file": Path(__file__).parent.parent.parent / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore unknown environment variables
    }


# Create a singleton instance that will be imported throughout the codebase
settings = Settings()