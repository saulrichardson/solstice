from pydantic_settings import BaseSettings
from pydantic import Field


# ---------------------------------------------------------------------------
# Centralised runtime configuration for the Solstice Gateway.  We tolerate
# unknown environment variables so that experiments or unrelated tooling
# don't crash the service (`extra = "ignore"`).  At the same time we expose
# explicit fields for every variable documented in `.env.example` so that
# IDE autocompletion and type checking still work.
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")

    # Gateway network settings (used when the process binds its socket)
    solstice_gateway_host: str = Field("0.0.0.0", alias="SOLSTICE_GATEWAY_HOST")
    solstice_gateway_port: int = Field(4000, alias="SOLSTICE_GATEWAY_PORT")

    # Optional convenience override – currently only used by clients but we
    # accept it here so that the variable doesn't raise a validation error.
    solstice_gateway_url: str | None = Field(None, alias="SOLSTICE_GATEWAY_URL")

    # Logging & cache toggles
    log_level: str = Field("INFO", alias="SOLSTICE_LOG_LEVEL")

    solstice_cache_enabled: bool = Field(True, alias="SOLSTICE_CACHE_ENABLED")
    solstice_cache_ttl: int = Field(3600, alias="SOLSTICE_CACHE_TTL")

    # Cache settings – filesystem based; Redis no longer used
    filesystem_cache_dir: str = Field(".cache", alias="FILESYSTEM_CACHE_DIR")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore undeclared env vars
        "populate_by_name": True,
    }


settings = Settings()
