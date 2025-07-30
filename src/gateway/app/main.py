import json
import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from .cache import cache
from .config import settings
from .middleware.logging import LoggingMiddleware, log_llm_request, log_llm_response
from .middleware.retry import RetryableProvider
from .openai_client import validate_api_key, OpenAIClientError
from .providers import OpenAIProvider, ResponseRequest

# Provider instances
providers = {}

# Set up logger
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await cache.connect()

    # Initialize providers with retry wrapper
    try:
        if validate_api_key():
            logger.debug("Creating OpenAI provider")
            providers["openai"] = RetryableProvider(OpenAIProvider())
            logger.debug(f"Provider created: {providers}")
    except OpenAIClientError as e:
        logger.warning(f"OpenAI client error: {e}")

    # Fail-fast: if no provider could be configured the gateway is unusable.
    if not providers:
        # Log a clear error message and abort startup so orchestration platforms
        # mark the container as failed rather than letting it run half-alive.
        logger.error(
            "Fatal: no LLM provider configured. Set OPENAI_API_KEY or "
            "check provider settings."
        )
        # Exit during lifespan startup phase.
        raise RuntimeError("No provider configured for Solstice Gateway")

    yield

    # Shutdown
    await cache.disconnect()


app = FastAPI(
    title="Solstice LLM Gateway",
    description="Gateway for OpenAI Responses API with GPT-4.1 and o4-mini",
    version="2.0.0",
    lifespan=lifespan,
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)


@app.get("/health")
async def health():
    """Health check endpoint."""
    healthy = bool(providers)

    payload = {
        "status": "healthy" if healthy else "unhealthy",
        "providers": list(providers.keys()),
        "cache_enabled": cache.cache_enabled,
        "api_version": "responses",
    }

    if not healthy:
        # Surface the problem clearly to callers (e.g., readiness probes).
        raise HTTPException(status_code=503, detail=payload)

    return payload


@app.post("/v1/responses")
async def create_response(request: Request, body: dict):
    """Main response creation endpoint using the Responses API."""
    request_id = request.state.request_id

    # Parse request
    try:
        response_request = ResponseRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # For now, we only support OpenAI provider
    provider_name = "openai"
    provider = providers.get(provider_name)
    if not provider:
        raise HTTPException(
            status_code=500, detail=f"Provider {provider_name} not configured"
        )

    # Log request
    log_llm_request(
        request_id, provider_name, response_request.model, response_request.model_dump()
    )

    # Prepare cache key for write-only snapshot (non-streaming, non-stateful requests)
    cache_key = None
    if not response_request.stream and not response_request.previous_response_id:
        # Create cache key from request
        cache_data = {
            "model": response_request.model,
            "input": response_request.input,
            "instructions": response_request.instructions,
            "tools": response_request.tools,
            "temperature": response_request.temperature,
        }
        # Note: Cache is write-only for audit/debugging purposes
        cache_key = cache_data

    # Check if streaming was requested and reject it
    if response_request.stream:
        raise HTTPException(
            status_code=400, 
            detail="Streaming is not supported by this gateway"
        )

    # Non-streaming response
    start_time = time.time()

    try:
        logger.debug("Calling provider.create_response")
        response = await provider.create_response(response_request)
        logger.debug("Got response back from provider")
        duration = time.time() - start_time

        # Log raw response for debugging
        response_dict = response.model_dump()
        logger.debug(f"Response dict keys: {list(response_dict.keys())}")
        logger.debug(f"Usage data: {response_dict.get('usage', 'NO USAGE KEY')}")

        # Log response
        log_llm_response(
            request_id,
            provider_name,
            response_request.model,
            response_dict,
            duration,
        )

        # Cache response if applicable
        if cache_key and not response_request.previous_response_id:
            await cache.set_response(cache_key, response_dict)

        return response_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider error: {e!s}")


@app.get("/v1/responses/{response_id}")
async def retrieve_response(response_id: str):
    """Retrieve a stored response."""
    provider = providers.get("openai")
    if not provider:
        raise HTTPException(status_code=500, detail="Provider not configured")

    try:
        response = await provider.retrieve_response(response_id)
        return response.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Response not found: {e!s}")


@app.delete("/v1/responses/{response_id}")
async def delete_response(response_id: str):
    """Delete a stored response."""
    provider = providers.get("openai")
    if not provider:
        raise HTTPException(status_code=500, detail="Provider not configured")

    try:
        result = await provider.delete_response(response_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Response not found: {e!s}")


@app.get("/models")
async def list_models():
    """List available OpenAI models."""
    # Return commonly used OpenAI models
    # Users can use any valid OpenAI model name
    return {
        "models": [
            {"id": "gpt-4.1", "provider": "openai"},
            {"id": "o4-mini", "provider": "openai"},
        ],
        "note": "You can use any valid OpenAI model name",
    }


@app.get("/api-info")
async def get_api_info():
    """Get information about the Responses API capabilities."""
    return {
        "api_version": "responses/v1",
        "features": {
            "roles": ["system", "developer", "user", "assistant", "function"],
            "conversation_storage": {
                "enabled": True,
                "method": "previous_response_id",
                "retention": "30 days",
            },
            "streaming": {
                "supported": True,
                "event_types": [
                    "response.text.delta",
                    "response.text.done",
                    "response.done",
                    "error",
                ],
            },
            "tools": {
                "custom_functions": True,
                "builtin_tools": ["web-search-preview", "code_interpreter"],
            },
            "response_format": {"json_schema": True, "structured_output": True},
            "parameters": {
                "temperature": "0.0-2.0",
                "top_p": "0.0-1.0",
                "presence_penalty": "-2.0-2.0",
                "frequency_penalty": "-2.0-2.0",
                "max_output_tokens": "Model dependent",
                "n": "Multiple completions",
                "timeout": "Request timeout in ms",
            },
        },
    }


@app.get("/pricing")
async def get_pricing():
    """Get current pricing information (as of 2025-07-26)."""
    return {
        "models": {
            "gpt-4.1": {
                "input": "$1.20 / M tokens",
                "output": "$4.80 / M tokens",
                "notes": "Full model, 1M context",
            },
            "gpt-4.1-mini": {
                "input": "$0.40 / M tokens",
                "output": "$1.60 / M tokens",
                "notes": "26% cheaper than GPT-4o, 1M context",
            },
            "gpt-4.1-nano": {
                "input": "$0.40 / M tokens",
                "output": "$1.60 / M tokens",
                "notes": "Fastest model, 1M context",
            },
            "o4-mini": {
                "input": "$1.10 / M tokens",
                "output": "$4.40 / M tokens",
                "notes": "Tool-driven reasoning, 200k context",
            },
        },
        "tools": {
            "code_interpreter": "$0.03 per run",
            "file_search": "$0.10 / GB·day storage + $2.50 / 1k calls",
            "image_generation": "$5 / M text in, $40 / M image out (only o3 today)",
        },
        "storage": {
            "responses": "30 days retention for stored conversations",
            "billing": "All tokens from stored turns are billed on each request",
        },
    }




if __name__ == "__main__":
    import uvicorn

    host = settings.solstice_gateway_host
    port = settings.solstice_gateway_port
    print(f"Starting Solstice Gateway on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
