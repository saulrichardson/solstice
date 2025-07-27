from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str | None = None
    
    # Gateway settings
    solstice_gateway_port: int = 4000
    log_level: str = "INFO"
    
    # Cache settings
    redis_url: str | None = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1 hour default
    
    # Model routing configuration for Responses API
    model_mapping: dict[str, dict] = {
        # GPT-4.1 family - 1M token context
        # Map to existing models until gpt-4.1 is available
        "gpt-4.1": {
            "provider": "openai",
            "model": "gpt-4-turbo",  # Map to gpt-4-turbo for now
            "max_tokens": 128000,  # Actual limit for gpt-4-turbo
            "supports_tools": True,
            "supports_reasoning": True
        },
        "gpt-4.1-mini": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",  # Map to gpt-3.5-turbo for now
            "max_tokens": 16385,  # Actual limit for gpt-3.5-turbo
            "supports_tools": True,
            "supports_reasoning": True
        },
        "gpt-4.1-nano": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",  # Map to gpt-3.5-turbo for now
            "max_tokens": 16385,  # Actual limit
            "supports_tools": True,
            "supports_reasoning": True
        },
        # o4-mini - tool-driven reasoning
        # Map to gpt-4-turbo until o4-mini is available
        "o4-mini": {
            "provider": "openai",
            "model": "gpt-4-turbo",  # Map to gpt-4-turbo for now
            "max_tokens": 128000,  # Actual limit
            "supports_tools": True,
            "supports_reasoning": True,
            "encrypted_reasoning": False,  # Not available yet
            # Built-in tools available for this model
            "builtin_tools": [
                "web-search-preview",
                "code_interpreter"
            ]
        }
    }
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


settings = Settings()
