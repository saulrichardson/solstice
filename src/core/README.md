# Core Module

Centralized configuration and shared utilities for the Solstice project.

## Overview

The core module serves as the foundation for the entire Solstice system, providing essential infrastructure components that ensure consistency and maintainability across all packages. It implements configuration management following 12-factor app principles.

### Key Responsibilities

- **Configuration Management**: Type-safe, environment-based settings using pydantic-settings
- **Settings Validation**: Automatic validation and type conversion of configuration values
- **Singleton Pattern**: Ensures consistent configuration access across the application
- **Computed Properties**: Dynamic URL construction and other derived values

## Components

### config.py

Centralized configuration management using pydantic-settings:

```python
from src.core.config import get_settings

# Access settings anywhere in the codebase
settings = get_settings()
gateway_url = settings.gateway_url
```

**Key Features:**
- Loads from environment variables and `.env` files
- Type validation and automatic conversion
- Computed properties for complex values
- Singleton pattern for consistent access

**Available Settings:**
- `solstice_gateway_url`: Full gateway URL (overrides host/port)
- `solstice_gateway_host`: Gateway hostname (default: localhost)
- `solstice_gateway_port`: Gateway port (default: 8000)
- `openai_api_key`: OpenAI API key for LLM calls
- `solstice_log_level`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `filesystem_cache_dir`: Base cache directory (default: data/cache)
- `text_extractor`: Text extraction method (default: pymupdf)

## Usage

### Environment Variables

Set configuration via environment:
```bash
export SOLSTICE_GATEWAY_URL=http://gateway.example.com:8080
export OPENAI_API_KEY=sk-...
export SOLSTICE_LOG_LEVEL=DEBUG
```

### .env File

Create a `.env` file in the project root:
```env
SOLSTICE_GATEWAY_URL=http://localhost:8000
OPENAI_API_KEY=sk-...
SOLSTICE_LOG_LEVEL=INFO
FILESYSTEM_CACHE_DIR=data/cache
```

### In Code

```python
from src.core.config import get_settings

def connect_to_gateway():
    settings = get_settings()
    url = settings.gateway_url  # Computed from URL or host/port
    
    # Use settings throughout your code
    if settings.solstice_log_level == "DEBUG":
        print(f"Connecting to gateway at {url}")
```

## Architecture Details

### Settings Class

The `Settings` class (defined in `config.py`) is the central configuration object:

- **Inheritance**: Extends `pydantic_settings.BaseSettings`
- **Validation**: Automatic type checking and conversion
- **Loading Order**: Environment variables → `.env` file → defaults
- **Computed Fields**: `gateway_url` property dynamically constructed from components

### Singleton Implementation

The `get_settings()` function implements a thread-safe singleton pattern:
```python
_settings_instance = None

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
```

This ensures all parts of the application share the same configuration instance.

## Design Principles

1. **Single Source of Truth**: All configuration centralized in one module
2. **Type Safety**: Pydantic provides runtime type validation
3. **Environment-First**: Follows 12-factor app principles for cloud-native deployment
4. **Minimal Dependencies**: Only requires pydantic-settings, no heavy frameworks
5. **Clear Defaults**: Sensible defaults enable zero-config local development
6. **Fail-Fast**: Invalid configuration causes immediate startup failure

## Integration with Other Modules

- **CLI**: Commands use `get_settings()` for configuration access
- **Gateway**: Reads API keys and connection settings
- **Ingestion**: Uses cache directory and processing settings
- **Fact Check**: Accesses model configurations and API endpoints

## Future Enhancements

- **Base Classes**: Abstract interfaces for agents, processors, and pipelines
- **Shared Utilities**: Common helper functions for logging, metrics, etc.
- **Error Types**: Standardized exception hierarchy for better error handling
- **Metrics Collection**: Centralized telemetry and instrumentation
- **Feature Flags**: Dynamic feature toggling without code changes
- **Secrets Management**: Integration with external secret stores