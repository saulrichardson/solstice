"""
Modern LLM client using the OpenAI Responses API.

This client talks to the Solstice Gateway that implements the OpenAI
"Responses" API.  The gateway itself may need an `OPENAI_API_KEY` to reach
OpenAI, but *clients are no longer required* to supply such a key.  An
`Authorization` header is only sent when an explicit key is provided.
"""
import json
import os
from collections.abc import Iterator

import httpx


class ResponsesClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        """
        Initialize client for the Responses API gateway.

        Args:
            base_url: Gateway URL, defaults to http://localhost:8000
            api_key: API key for authentication
        """
        default_port = os.getenv("SOLSTICE_GATEWAY_PORT", "8000")
        default_url = f"http://localhost:{default_port}"

        self.base_url = base_url or os.getenv("SOLSTICE_GATEWAY_URL", default_url)

        # ------------------------------------------------------------------
        # Authentication header is optional.  Historically we forwarded the
        # user's personal OpenAI key to the gateway, but the gateway never
        # validated it.  To avoid needless friction we now only attach the
        # header when an explicit `api_key` is supplied or the developer sets
        # OPENAI_API_KEY in their environment for another reason.
        # ------------------------------------------------------------------

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def create_response(
        self,
        input: str | list[dict] | None = None,
        model: str = "gpt-4.1-mini",
        previous_response_id: str | None = None,
        instructions: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = "auto",
        parallel_tool_calls: bool = True,
        store: bool = True,
        reasoning: dict | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
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
            store: Store the response for retrieval
            reasoning: Reasoning configuration for o4-mini
            temperature: Sampling temperature
            max_output_tokens: Maximum output tokens

        Returns:
            Response object with output, tool calls, and usage info
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
        if store is not None:
            request_data["store"] = store
        if reasoning:
            request_data["reasoning"] = reasoning
        if temperature is not None:
            request_data["temperature"] = temperature
        if max_output_tokens is not None:
            request_data["max_output_tokens"] = max_output_tokens

        # Add any extra kwargs
        request_data.update(kwargs)

        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/v1/responses",
                json=request_data,
                headers=self.headers,
                timeout=120.0,
            )
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 500:
                    error_detail = e.response.json().get("detail", "")
                    if "OpenAI SDK does not support Responses API" in error_detail:
                        raise RuntimeError(
                            "Gateway requires OpenAI SDK >= 1.50.0 for Responses API support. "
                            "Please upgrade the SDK on the gateway server."
                        ) from e
                raise

    def stream_response(
        self,
        input: str | list[dict] | None = None,
        model: str = "gpt-4.1-mini",
        **kwargs,
    ) -> Iterator[dict]:
        """
        Stream a response for real-time output.

        Yields:
            Response chunks as they arrive
        """
        request_data = {"model": model, "stream": True}

        if input is not None:
            request_data["input"] = input

        request_data.update(kwargs)

        with httpx.Client() as client:
            with client.stream(
                "POST",
                f"{self.base_url}/v1/responses",
                json=request_data,
                headers=self.headers,
                timeout=120.0,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue

    def retrieve_response(self, response_id: str) -> dict:
        """
        Retrieve a stored response.

        Args:
            response_id: The ID of the response to retrieve

        Returns:
            The stored response object
        """
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/v1/responses/{response_id}", headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def delete_response(self, response_id: str) -> dict:
        """
        Delete a stored response.

        Args:
            response_id: The ID of the response to delete

        Returns:
            Deletion confirmation
        """
        with httpx.Client() as client:
            response = client.delete(
                f"{self.base_url}/v1/responses/{response_id}", headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    def complete(self, prompt: str, model: str = "gpt-4.1-mini", **kwargs) -> str:
        """
        Simple completion wrapper for basic use cases.

        Args:
            prompt: The user prompt
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            The assistant's response as a string
        """
        response = self.create_response(input=prompt, model=model, **kwargs)
        return response.get("output_text", "")

    def complete_with_tools(
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
        return self.create_response(input=prompt, model=model, tools=tools, **kwargs)

    def complete_with_reasoning(
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

        response = self.create_response(
            input=prompt, model=model, reasoning=reasoning_config, **kwargs
        )
        return response.get("output_text", "")

    def create_stateful_conversation(
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
        return self.create_response(
            input=initial_message,
            model=model,
            instructions=instructions,
            store=True,
            **kwargs,
        )

    def continue_conversation(
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
        return self.create_response(
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
