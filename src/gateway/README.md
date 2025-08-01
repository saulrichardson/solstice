# Gateway Module

HTTP service that handles all LLM API calls for the Solstice system.

## Overview

The gateway acts as a proxy between Solstice components and OpenAI's API. All fact-checking agents send their requests through this service.

### What it does:
- Receives LLM requests from fact-checking agents
- Forwards them to OpenAI API
- Saves responses to disk for debugging
- Retries failed requests automatically

## Key Components

- **FastAPI app** (`main.py`) - HTTP server
- **OpenAI provider** - Handles API calls to OpenAI
- **Cache** - Saves all responses to `data/gateway_cache/`
- **Retry logic** - Automatically retries failed requests

## API Endpoints

### Health Check
```bash
GET /health
```
Returns provider status and configuration.

### Create Response
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
export FILESYSTEM_CACHE_DIR=data/gateway_cache

# Run the service
uvicorn src.gateway.app.main:app --reload --port 8000
```

## Configuration

### Required Environment Variables
- `OPENAI_API_KEY` - Your OpenAI API key

### Optional Environment Variables
- `FILESYSTEM_CACHE_DIR` - Directory for audit logs (default: `data/gateway_cache`)
- `SOLSTICE_LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)
- `SOLSTICE_GATEWAY_HOST` - Bind host (default: `0.0.0.0`)
- `SOLSTICE_GATEWAY_PORT` - Bind port (default: `8000`)

## Response Caching

The gateway saves all LLM responses to disk for debugging:
- Location: `data/gateway_cache/`
- Format: JSON files with hashed names
- Note: This is write-only - requests always go to OpenAI

## Error Handling

The gateway automatically retries failed requests up to 3 times with increasing delays.

## Monitoring

- Check `/health` endpoint for service status
- View logs for request/response details
- All responses saved in cache directory

## Troubleshooting

- **Gateway won't start**: Check `OPENAI_API_KEY` is set
- **No cache files**: Verify write permissions on cache directory
- **Slow responses**: Check if requests are being retried in logs