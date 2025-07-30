# Solstice Gateway

A lightweight proxy service for OpenAI's Responses API with audit logging and retry capabilities.

## Overview

The Gateway provides a unified interface to OpenAI's Responses API with:
- **Write-only audit logging** - All responses saved to disk for debugging/analysis
- **Automatic retry logic** - Handles transient failures with exponential backoff
- **Request/response logging** - Structured logs for monitoring
- **Streaming support** - Efficient handling of streaming responses

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
                      ┌──────────┴──────────┐
                      │                     │
              ┌───────▼────────┐    ┌──────▼──────┐
              │ OpenAI Responses│    │ Filesystem  │
              │      API        │    │ Audit Logs  │
              └────────────────┘    └─────────────┘
```

### Key Components

- **`main.py`** - FastAPI application with lifecycle management
- **`providers/`** - Provider abstraction layer
  - `base.py` - Abstract provider interface using Responses API format
  - `openai_provider.py` - OpenAI Responses API implementation
- **`middleware/`** - Cross-cutting concerns
  - `retry.py` - Automatic retry with exponential backoff
  - `logging.py` - Structured request/response logging
- **`cache.py`** - Write-only filesystem audit log
- **`config.py`** - Environment-based configuration

## API Endpoints

### Health Check
```bash
GET /health
```
Returns provider status and configuration.

### Create Response (OpenAI Responses API)
```bash
POST /v1/responses

{
  "model": "gpt-4.1",
  "input": "What is the capital of France?",
  "instructions": "Answer concisely",
  "temperature": 0.7,
  "stream": false
}
```

### Retrieve Response
```bash
GET /v1/responses/{response_id}
```

### Delete Response
```bash
DELETE /v1/responses/{response_id}
```

### List Available Models
```bash
GET /models
```

## Running the Service

### Docker (Recommended)
```bash
# Start the service
docker compose up -d

# View logs
docker compose logs -f gateway

# Stop the service
docker compose down
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=sk-...
export FILESYSTEM_CACHE_DIR=data/cache/gateway

# Run the service
uvicorn src.gateway.app.main:app --reload --port 8000
```

## Configuration

### Required Environment Variables
- `OPENAI_API_KEY` - Your OpenAI API key

### Optional Environment Variables
- `FILESYSTEM_CACHE_DIR` - Directory for audit logs (default: `data/cache/gateway`)
- `SOLSTICE_LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)
- `SOLSTICE_GATEWAY_HOST` - Bind host (default: `0.0.0.0`)
- `SOLSTICE_GATEWAY_PORT` - Bind port (default: `8000`)

## Audit Logging

The gateway maintains a write-only audit log of all responses:

1. **Purpose**: Debugging, analysis, and compliance
2. **Format**: JSON files named by SHA-256 hash of request parameters
3. **Location**: `FILESYSTEM_CACHE_DIR` directory
4. **Behavior**: Responses are NEVER read from cache - all requests go to OpenAI

Example audit log structure:
```
data/cache/gateway/
├── a1b2c3d4...json  # Response for request hash a1b2c3d4
├── e5f6g7h8...json  # Response for request hash e5f6g7h8
└── ...
```

## Error Handling

### Automatic Retry
- **Attempts**: 3 (configurable)
- **Backoff**: 0.5s, 1s, 2s (exponential)
- **Retryable errors**: Network failures, 5xx errors, timeouts

### Error Response Format
```json
{
  "detail": "Provider error: Connection timeout"
}
```

## Streaming Support

For streaming responses, use `stream: true`:

```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        'POST',
        'http://localhost:8000/v1/responses',
        json={
            "model": "gpt-4.1",
            "input": "Write a story",
            "stream": True
        }
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith('data: '):
                data = line[6:]  # Remove 'data: ' prefix
                if data != '[DONE]':
                    chunk = json.loads(data)
                    print(chunk)
```

## Monitoring

### Logs
Structured logs include:
- Request ID for correlation
- Model and provider information
- Response times
- Token usage

Example:
```
[gateway] Request: model=gpt-4.1, provider=openai
[gateway] Response: model=gpt-4.1, duration=1.2s, tokens={"input": 10, "output": 50}
```

### Health Monitoring
The `/health` endpoint provides:
- Service status
- Available providers
- Cache status
- API version

## Security

- API keys are never logged
- Request/response payloads logged only at DEBUG level
- Audit logs use hashed filenames (no PII in paths)
- All provider communication uses HTTPS

## Extending the Gateway

### Adding a New Provider

1. Implement the provider interface:
```python
from providers.base import Provider, ResponseRequest, ResponseObject

class NewProvider(Provider):
    async def create_response(self, request: ResponseRequest) -> ResponseObject:
        # Implementation
        pass
```

2. Register in `main.py` during startup:
```python
providers["new_provider"] = RetryableProvider(NewProvider())
```

## Troubleshooting

### Gateway won't start
- Check `OPENAI_API_KEY` is set
- Verify network connectivity to OpenAI
- Check logs for specific errors

### Responses not being cached
- Verify `FILESYSTEM_CACHE_DIR` exists and is writable
- Check disk space
- Look for cache write errors in logs

### High latency
- Check retry logs - frequent retries indicate API issues
- Monitor OpenAI API status
- Consider adjusting timeout settings