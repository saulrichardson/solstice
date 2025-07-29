# Core Module

Centralized configuration and shared utilities for the Solstice project.

## Overview

The core module provides foundational components used across all Solstice packages:
- **Configuration Management**: Environment-based settings using pydantic-settings
- **Shared Constants**: Common values and defaults
- **Base Classes**: Abstract interfaces (future)

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

## Design Principles

1. **Single Source of Truth**: All configuration in one place
2. **Type Safety**: Pydantic validates all settings
3. **Environment-First**: Follows 12-factor app principles
4. **Minimal Dependencies**: Only requires pydantic-settings
5. **Clear Defaults**: Sensible defaults for local development

## Future Enhancements

- **Base Classes**: Abstract interfaces for agents and processors
- **Shared Utilities**: Common helper functions
- **Error Types**: Standardized exception hierarchy
- **Metrics Collection**: Centralized instrumentation