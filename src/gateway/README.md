# Solstice Gateway

A lightweight proxy service for OpenAI's Responses API with audit logging and retry capabilities.

## Overview

The Gateway serves as a centralized access point for all LLM interactions in the Solstice system. It provides a unified interface to OpenAI's Responses API with enterprise-grade features:

- **Write-only audit logging** - All responses saved to disk for debugging/analysis
- **Automatic retry logic** - Handles transient failures with exponential backoff
- **Request/response logging** - Structured logs for monitoring and debugging
- **Provider abstraction** - Extensible architecture for multiple LLM providers
- **Fail-fast startup** - Validates configuration before accepting requests

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

- **`main.py`** - FastAPI application with lifecycle management and provider initialization
- **`providers/`** - Provider abstraction layer for LLM services
  - `base.py` - Abstract provider interface defining the Responses API contract
  - `openai_provider.py` - OpenAI Responses API implementation with proper error handling
- **`middleware/`** - Cross-cutting concerns and request processing
  - `retry.py` - Automatic retry with exponential backoff for transient failures
  - `logging.py` - Structured request/response logging with correlation IDs
- **`cache.py`** - Write-only filesystem audit log for compliance and debugging
- **`config.py`** - Environment-based configuration using pydantic
- **`openai_client.py`** - OpenAI client wrapper with validation and error handling

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
  "temperature": 0.7
}
```


## Running the Service

### Docker (Recommended)

The gateway is managed through the root Makefile:

```bash
# From the repository root:

# Start all services (including gateway)
make up

# View gateway logs
make logs

# Stop all services
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
- **Attempts**: 3 (default)
- **Backoff**: 0.5s, 1s, 2s (exponential with base 0.5s)
- **Retryable errors**: All exceptions (network failures, API errors, timeouts)

### Error Response Format
```json
{
  "detail": "Provider error: Connection timeout"
}
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

1. Create a new provider class in `providers/`:
```python
from .base import Provider, ResponseRequest, ResponseObject

class NewProvider(Provider):
    async def create_response(self, request: ResponseRequest) -> ResponseObject:
        # Implement the Responses API contract
        # Handle authentication, API calls, and error mapping
        pass
    
    def validate_config(self) -> bool:
        # Validate provider-specific configuration
        return True
```

2. Register in `main.py` during the lifespan startup:
```python
# In lifespan() function
if new_provider_configured():
    providers["new_provider"] = RetryableProvider(NewProvider())
```

3. Add provider-specific configuration to `config.py` if needed

### Architecture Principles

1. **Provider Independence**: All providers implement the same interface
2. **Retry Wrapper**: Providers are wrapped with retry logic automatically
3. **Audit Everything**: All responses are logged, never read from cache
4. **Fail Fast**: Invalid configuration prevents startup
5. **Structured Logging**: All logs include correlation IDs and metadata

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