import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from .cache import cache
from .config import settings
from .middleware.logging import LoggingMiddleware, log_llm_request, log_llm_response
from .middleware.retry import RetryableProvider
from .providers import OpenAIProvider, ResponseRequest

# Provider instances
providers = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await cache.connect()

    # Initialize providers with retry wrapper
    if settings.openai_api_key:
        providers["openai"] = RetryableProvider(OpenAIProvider())

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
    return {
        "status": "healthy",
        "providers": list(providers.keys()),
        "cache_enabled": cache.enabled,
        "api_version": "responses",
    }


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

    # Check cache (only for non-streaming and non-stateful requests)
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
        cached = await cache.get_response(cache_data)
        if cached:
            return cached
        cache_key = cache_data

    # Handle streaming
    if response_request.stream:

        async def stream_generator():
            async for chunk in provider.stream_response(response_request):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming response
    start_time = time.time()

    try:
        response = await provider.create_response(response_request)
        duration = time.time() - start_time

        # Log response
        log_llm_response(
            request_id,
            provider_name,
            response_request.model,
            response.model_dump(),
            duration,
        )

        # Cache response if applicable
        response_dict = response.model_dump()
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

    port = settings.solstice_gateway_port
    print(f"Starting Solstice Gateway on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
