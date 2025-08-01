# Core Module

Shared configuration settings for Solstice.

## Overview

The core module provides configuration management for all Solstice components. It reads settings from environment variables and makes them available throughout the codebase.

## What it provides

### Configuration Settings
- Gateway URL and connection details
- OpenAI API key
- Log level (DEBUG, INFO, etc.)
- Cache directory paths

### How to use
```python
from src.core.config import settings

# Access any setting
gateway_url = settings.gateway_url
api_key = settings.openai_api_key
```

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
FILESYSTEM_CACHE_DIR=data/scientific_cache
```

### In Code

```python
from src.core.config import settings

def connect_to_gateway():
    url = settings.gateway_url  # Computed from URL or host/port
    
    # Use settings throughout your code
    if settings.solstice_log_level == "DEBUG":
        print(f"Connecting to gateway at {url}")
```

## Integration

All Solstice modules use this configuration:
- CLI commands get paths and settings
- Gateway gets API keys
- Fact-checking gets model names
- Ingestion gets cache directories