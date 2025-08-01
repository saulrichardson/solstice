# Core Module

Central configuration for Solstice.

## What it provides

Environment-based settings accessible throughout the codebase:
- Gateway URL
- OpenAI API key  
- Log level
- Cache directories

## Usage

```python
from src.core.config import settings

url = settings.gateway_url
api_key = settings.openai_api_key
```

## Configuration

Set via environment variables:
```bash
export OPENAI_API_KEY=sk-...
export SOLSTICE_LOG_LEVEL=INFO
```

Or create `.env` file in project root.