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
    
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False
    }


settings = Settings()
