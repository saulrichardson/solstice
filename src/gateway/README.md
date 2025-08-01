# Gateway Module

HTTP proxy for LLM API calls.

## What it does

- Receives requests from fact-checking agents
- Forwards to OpenAI API
- Saves responses to disk
- Retries failed requests

## Running

```bash
# With Docker (recommended)
make up

# Local development
export OPENAI_API_KEY=sk-...
uvicorn src.gateway.app.main:app --port 8000
```

## Configuration

- `OPENAI_API_KEY` - Required
- `FILESYSTEM_CACHE_DIR` - Where to save responses (default: `data/gateway_cache`)

## Endpoints

- `POST /v1/responses` - Create LLM response
- `GET /health` - Check service status