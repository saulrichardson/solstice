"""
Modern LLM client using the OpenAI Responses API.

This client talks to the Solstice Gateway that implements the OpenAI
"Responses" API.  The gateway itself may need an `OPENAI_API_KEY` to reach
OpenAI, but *clients are no longer required* to supply such a key.  An
`Authorization` header is only sent when an explicit key is provided.
"""
import logging

import httpx

from src.core.config import settings
try:
    from ..config.model_capabilities import extract_text_from_response
except ImportError:
    # Handle import when module is used outside fact_check context
    from src.fact_check.config.model_capabilities import extract_text_from_response

logger = logging.getLogger(__name__)


class ResponsesClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        """
        Initialize client for the Responses API gateway.

        Args:
            base_url: Gateway URL (required if SOLSTICE_GATEWAY_URL not set)
            api_key: API key for authentication
        """
        # Use provided base_url or get from centralized settings
        self.base_url = base_url or settings.gateway_url
        # Normalize URL to remove trailing slash
        self.base_url = self.base_url.rstrip("/")

        # ------------------------------------------------------------------
        # Authentication header is optional.  Historically we forwarded the
        # user's personal OpenAI key to the gateway, but the gateway never
        # validated it.  To avoid needless friction we now only attach the
        # header when an explicit `api_key` is supplied or the developer sets
        # OPENAI_API_KEY in their environment for another reason.
        # ------------------------------------------------------------------

        self.api_key = api_key or settings.openai_api_key

        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def create_response(
        self,
        input: str | list[dict] | None = None,
        model: str = "gpt-4.1-mini",
        previous_response_id: str | None = None,
        instructions: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = "auto",
        parallel_tool_calls: bool = True,
        store: bool = False,
        reasoning: dict | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        *,
        fresh_response: bool = True,
        **kwargs,
    ) -> dict:
        """
        Create a response using the Responses API.

        Args:
            input: Text or message history
            model: Model to use (gpt-4.1, gpt-4.1-mini, o4-mini, etc.)
            previous_response_id: ID for stateful conversations
            instructions: System-level instructions
            tools: Tool definitions (web_search_preview, code_interpreter, etc.)
            tool_choice: Tool selection strategy
            parallel_tool_calls: Allow parallel tool execution
            store: Whether to persist response on server for later retrieval (default: False)
            reasoning: Reasoning configuration for o4-mini
            temperature: Sampling temperature
            max_output_tokens: Maximum output tokens
            fresh_response: If True (default), ensures each request gets a fresh response
                by adding a unique nonce. If False, allows cached responses for identical 
                requests, improving speed and reducing costs.

        Returns:
            Response object with output, tool calls, and usage info
            
        Note on Caching:
            - Request deduplication (controlled by fresh_response parameter) determines
              whether identical API requests return identical cached responses
            - Response storage (controlled by store) determines whether responses are 
              persisted on the server for later retrieval via response_id
            - These are independent: you can have fresh responses that aren't stored,
              or deduplicated responses that are stored
        """
        request_data = {
            "model": model,
        }

        # Add optional fields
        if input is not None:
            request_data["input"] = input
        if previous_response_id:
            request_data["previous_response_id"] = previous_response_id
        if instructions:
            request_data["instructions"] = instructions
        if tools:
            request_data["tools"] = tools
        if tool_choice is not None:
            request_data["tool_choice"] = tool_choice
        if parallel_tool_calls is not None:
            request_data["parallel_tool_calls"] = parallel_tool_calls
        # By default we do *not* store responses on the server.  The caller
        # must explicitly request persistence by passing store=True.
        request_data["store"] = store
        if reasoning:
            request_data["reasoning"] = reasoning
        if temperature is not None:
            request_data["temperature"] = temperature
        if max_output_tokens is not None:
            request_data["max_output_tokens"] = max_output_tokens

        # ------------------------------------------------------------------
        # Request deduplication prevention: when fresh_response=True (default)
        # we attach a nonce to metadata to ensure that subsequent identical calls
        # still go through the model rather than returning a cached response.
        # The nonce lives in `metadata` which is excluded from the prompt and
        # therefore does not influence the model or incur token costs.
        # ------------------------------------------------------------------

        if fresh_response:
            from src.util.nonce import new_nonce  # local import to avoid cycles

            nonce = new_nonce()

            # Merge with any user-supplied metadata
            metadata = request_data.get("metadata", {})
            # We avoid overwriting an existing nonce key to keep idempotency if
            # the caller purposely sets their own marker.
            metadata.setdefault("nonce", nonce)
            request_data["metadata"] = metadata

        # Add any extra kwargs (after nonce injection so that explicit kwargs
        # always win over internal defaults).
        request_data.update(kwargs)
        
        # Debug logging for LLM calls
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"\n{'='*60}")
            logger.debug(f"🤖 LLM CALL - Model: {model}")
            logger.debug(f"🌡️  Temperature: {temperature if temperature is not None else 'default'}")
            logger.debug(f"📊 Max tokens: {max_output_tokens if max_output_tokens is not None else 'default'}")
            logger.debug(f"🔄 Fresh responses: {'ENABLED' if fresh_response else 'DISABLED'}")
            logger.debug(f"💾 Response storage: {'ENABLED' if store else 'DISABLED'}")
            prompt = input if isinstance(input, str) else str(input)[:500]
            logger.debug(f"📝 Prompt preview: {prompt[:200]}..." if len(prompt) > 200 else f"📝 Prompt: {prompt}")
            logger.debug(f"{'='*60}\n")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/responses",
                json=request_data,
                headers=self.headers,
                timeout=600.0,  # 10 minutes for complex medical documents
            )
            try:
                response.raise_for_status()
                result = response.json()
                
                # Debug log the response
                if logger.isEnabledFor(logging.DEBUG):
                    try:
                        text = self.extract_text(result)
                        logger.debug(f"\n{'='*60}")
                        logger.debug(f"✅ LLM RESPONSE")
                        logger.debug(f"📄 Response preview: {text[:300]}..." if len(text) > 300 else f"📄 Response: {text}")
                        
                        # Log usage information if available
                        if "usage" in result:
                            usage = result["usage"]
                            logger.debug(f"📊 Token Usage:")
                            logger.debug(f"   - Total tokens: {usage.get('total_tokens', 'N/A')}")
                            # Support both Chat Completions API and Responses API field names
                            input_tokens = usage.get('input_tokens', usage.get('prompt_tokens', 'N/A'))
                            output_tokens = usage.get('output_tokens', usage.get('completion_tokens', 'N/A'))
                            logger.debug(f"   - Input tokens: {input_tokens}")
                            logger.debug(f"   - Output tokens: {output_tokens}")
                            
                            # Check for cached tokens in input_tokens_details (Responses API) or prompt_tokens_details (Chat API)
                            details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details")
                            if details:
                                cached_tokens = details.get("cached_tokens", 0)
                                logger.debug(f"   - Cached tokens: {cached_tokens}")
                                if cached_tokens > 0:
                                    logger.debug(f"   ⚡ CACHE HIT: {cached_tokens} tokens were cached!")
                        
                        logger.debug(f"{'='*60}\n")
                    except Exception as e:
                        logger.debug(f"✅ LLM Response received (could not extract text: {e})")
                
                return result
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 500:
                    error_detail = e.response.json().get("detail", "")
                    if "OpenAI SDK does not support Responses API" in error_detail:
                        raise RuntimeError(
                            "Gateway requires OpenAI SDK >= 1.50.0 for Responses API support. "
                            "Please upgrade the SDK on the gateway server."
                        ) from e
                raise
    
    def extract_text(self, response: dict, model: str = None) -> str:
        """
        Extract text content from Responses API response.
        
        Args:
            response: Response dict from create_response()
            model: Model name (if None, tries to extract from response)
            
        Returns:
            str: Extracted text content
            
        Raises:
            ValueError: If response doesn't match expected format
        """
        # Try to get model from response if not provided
        if model is None:
            model = response.get("model", "gpt-4.1")
        
        # Use model-specific extraction
        return extract_text_from_response(response, model)


    async def complete(self, prompt: str, model: str = "gpt-4.1-mini", **kwargs) -> str:
        """
        Simple completion wrapper for basic use cases.

        Args:
            prompt: The user prompt
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            The assistant's response as a string
        """
        response = await self.create_response(input=prompt, model=model, **kwargs)
        return response.get("output_text", "")
    

    async def complete_with_tools(
        self, prompt: str, tools: list[dict], model: str = "gpt-4.1-mini", **kwargs
    ) -> dict:
        """
        Complete with tool support.

        Args:
            prompt: The user prompt
            tools: Tool definitions or built-in tool names
            model: Model to use

        Returns:
            Response object with potential tool calls

        Example:
            # Using built-in tools
            response = client.complete_with_tools(
                "Search for recent AI news",
                tools=["web-search-preview"]
            )

            # Using custom tools
            response = client.complete_with_tools(
                "Calculate the area of a circle with radius 5",
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "calculate_area",
                        "description": "Calculate circle area",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "radius": {"type": "number"}
                            },
                            "required": ["radius"]
                        }
                    }
                }]
            )
        """
        return await self.create_response(input=prompt, model=model, tools=tools, **kwargs)

    async def complete_with_reasoning(
        self,
        prompt: str,
        model: str = "o4-mini",
        reasoning_level: str = "medium",
        **kwargs,
    ) -> str:
        """
        Use reasoning models with encrypted reasoning.

        Args:
            prompt: The prompt
            model: o4-mini or other reasoning model
            reasoning_level: "low", "medium", or "high"

        Returns:
            The reasoned response
        """
        reasoning_config = {"level": reasoning_level}

        response = await self.create_response(
            input=prompt, model=model, reasoning=reasoning_config, **kwargs
        )
        return response.get("output_text", "")

    async def create_stateful_conversation(
        self,
        initial_message: str,
        model: str = "gpt-4.1-mini",
        instructions: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Start a stateful conversation.

        Args:
            initial_message: The first message
            model: Model to use
            instructions: System instructions

        Returns:
            Response with ID for continuation
        """
        return await self.create_response(
            input=initial_message,
            model=model,
            instructions=instructions,
            store=True,
            **kwargs,
        )

    async def continue_conversation(
        self,
        message: str,
        previous_response_id: str,
        model: str = "gpt-4.1-mini",
        **kwargs,
    ) -> dict:
        """
        Continue a stateful conversation.

        Args:
            message: The next message
            previous_response_id: ID from previous response
            model: Model to use (should match previous)

        Returns:
            Response with new ID for further continuation
        """
        return await self.create_response(
            input=message,
            model=model,
            previous_response_id=previous_response_id,
            store=True,
            **kwargs,
        )
    


# ---------------------------------------------------------------------------
# Note for maintainers:
# The extensive interactive example that previously lived at the bottom of
# this module has been removed to keep the library import-side-effect free.
# A copy of the example can now be found in the project documentation folder
# (docs/usage_examples.md) and in the tests that exercise the high-level API.
# ---------------------------------------------------------------------------
