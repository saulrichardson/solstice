# Gateway Service

A unified proxy service for LLM API calls with caching, retry logic, and provider abstraction.

## Overview

The Gateway service acts as an intermediary between Solstice components and external LLM providers (OpenAI, Anthropic, etc.). It provides:
- **Provider Abstraction**: Unified interface for multiple LLM providers
- **Request Snapshots**: Filesystem-based write-only cache for audit/debugging
- **Retry Logic**: Automatic retry with exponential backoff
- **Request Logging**: Detailed logging for debugging and monitoring
- **Streaming Support**: Efficient handling of streaming responses

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Fact Checker   │     │   Ingestion     │     │  Other Clients  │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         └───────────────────────┴─────────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │    Gateway     │
                         │   (FastAPI)    │
                         └───────┬────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
        ┌───────▼────────┐ ┌────▼─────┐ ┌───────▼────────┐
        │     OpenAI     │ │Filesystem│ │   Anthropic    │
        │   Provider     │ │Snapshots │ │   Provider     │
        └────────────────┘ └──────────┘ └────────────────┘
```

## Components

### App Structure
- **main.py**: FastAPI application and lifecycle management
- **config.py**: Environment-based configuration
- **cache.py**: Filesystem-based snapshot implementation (write-only)
- **openai_client.py**: OpenAI API client wrapper

### Middleware
- **logging.py**: Request/response logging middleware
- **retry.py**: Automatic retry with exponential backoff

### Providers
- **base.py**: Abstract base provider interface
- **openai_provider.py**: OpenAI implementation

## Running the Service

### Docker (Recommended)
```bash
# Start the service
make up

# View logs
make logs

# Stop the service
make down
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=sk-...
export FILESYSTEM_CACHE_DIR=data/cache/gateway

# Run the service
uvicorn src.gateway.app.main:app --reload
```

## API Endpoints

### Health Check
```bash
GET /
```

### Create Completion
```bash
POST /v1/completions

{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "temperature": 0.7,
  "stream": false
}
```

### Streaming Example
```python
import requests

response = requests.post(
    "http://localhost:8000/v1/completions",
    json={
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key (required)
- `FILESYSTEM_CACHE_DIR`: Directory for response snapshots (default: data/cache)
- `LOG_LEVEL`: Logging level (default: INFO)

### Provider Configuration
Providers are automatically initialized based on available API keys:
```python
# In main.py
if validate_api_key():
    providers["openai"] = RetryableProvider(OpenAIProvider())
```

## Snapshot Strategy

The gateway uses filesystem-based snapshots for audit and debugging:
1. **Snapshot Key**: SHA-256 hash of request parameters (model, messages, temperature, etc.)
2. **Write-Only**: Snapshots are never read during normal operation (always makes live requests)
3. **Purpose**: Audit trail and debugging of LLM interactions
4. **Location**: Stored in `FILESYSTEM_CACHE_DIR` as JSON files

## Error Handling

### Retry Logic
- Automatic retry for transient errors (network, rate limits)
- Exponential backoff: 1s, 2s, 4s
- Maximum 3 attempts by default

### Error Responses
```json
{
  "detail": "Error message",
  "provider": "openai",
  "status_code": 429
}
```

## Monitoring

### Logs
The gateway logs all requests and responses:
```
[gateway] Request: model=gpt-4, messages=1, temperature=0.7
[gateway] Response: model=gpt-4, usage={"prompt_tokens": 10, "completion_tokens": 20}
```

### Health Monitoring
- Health endpoint at `/`
- Startup validation ensures at least one provider is configured
- Graceful shutdown on SIGTERM

## Adding New Providers

1. Create a new provider in `providers/`:
```python
from .base import BaseProvider

class AnthropicProvider(BaseProvider):
    async def create_completion(self, request: ResponseRequest):
        # Implementation
        pass
```

2. Register in `main.py`:
```python
if settings.anthropic_api_key:
    providers["anthropic"] = RetryableProvider(AnthropicProvider())
```

3. Add configuration in `config.py`:
```python
anthropic_api_key: str | None = Field(None)
```

## Security Considerations

- API keys are never logged
- Request/response bodies are logged at DEBUG level only
- Snapshot filenames are SHA-256 hashes (no sensitive data in filenames)
- All external API calls use HTTPS

## Future Enhancements

- **Multi-Provider Routing**: Route requests to different providers based on model
- **Cost Tracking**: Track and report API usage costs
- **Rate Limiting**: Per-client rate limiting
- **Metrics Export**: Prometheus/OpenTelemetry integration
- **Request Queuing**: Queue management for high load