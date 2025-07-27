import json
from typing import AsyncIterator
import openai
from openai import AsyncOpenAI
import logging

from .base import Provider, ResponseRequest, ResponseObject
from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    """OpenAI provider using the Responses API"""
    
    def _extract_text_from_response(self, response_dict: dict) -> str | None:
        """Extract text from various response formats."""
        # Check for direct output_text
        if 'output_text' in response_dict:
            return response_dict['output_text']
        
        # Check for choices format (ChatCompletion style)
        if 'choices' in response_dict and response_dict['choices']:
            first_choice = response_dict['choices'][0]
            if 'message' in first_choice and 'content' in first_choice['message']:
                return first_choice['message']['content']
            elif 'text' in first_choice:
                return first_choice['text']
        
        # Check for output array format
        if 'output' in response_dict and isinstance(response_dict['output'], list):
            for item in response_dict['output']:
                if not isinstance(item, dict):
                    continue

                # Old/standard format: {"role": "assistant", "content": "..."}
                if item.get('role') == 'assistant' and 'content' in item:
                    return item['content']

                # New beta format: {"type": "message", "content": [{"type": "output_text", "text": "..."}]}
                if item.get('type') == 'message' and isinstance(item.get('content'), list):
                    for content_item in item['content']:
                        if (
                            isinstance(content_item, dict)
                            and content_item.get('type') == 'output_text'
                            and 'text' in content_item
                        ):
                            return content_item['text']
        
        return None
    
    def _normalize_response(self, response_dict: dict) -> dict:
        """Normalize response to handle different SDK versions and beta bugs."""
        # No legacy normalisation: gateway expects the latest nested structure
        return response_dict
    
    def _normalize_tools(self, tools: list[str | dict] | None) -> list[dict] | None:
        """Normalize tool definitions to match API expectations."""
        if not tools:
            return None
        
        normalized = []
        for tool in tools:
            # Handle built-in tools passed as strings
            if isinstance(tool, str):
                # Convert underscore to hyphen for built-in tools
                if tool == "web_search_preview":
                    tool = "web-search-preview"
                normalized.append({"type": tool})
            elif isinstance(tool, dict):
                # Handle custom function tools
                if "type" not in tool and "function" in tool:
                    tool = {"type": "function", "function": tool["function"]}
                # Handle built-in tools with configuration
                elif tool.get("type") == "code_interpreter" and "container" not in tool:
                    tool = dict(tool)  # Create a copy to avoid modifying the original
                    tool["container"] = {"type": "auto"}
                normalized.append(tool)
            else:
                normalized.append(tool)
        
        return normalized
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Log SDK version for debugging
        logger.info(f"Using OpenAI SDK version: {openai.__version__}")
    
    async def create_response(self, request: ResponseRequest) -> ResponseObject:
        """Create a response using OpenAI's Responses API"""
        
        # Get the actual model name from config
        from ..config import settings
        model_config = settings.model_mapping.get(request.model, {})
        actual_model = model_config.get("model", request.model)
        
        # Build the API request
        api_request = {
            "model": actual_model,
        }
        
        # Add optional fields only if provided
        if request.input is not None:
            api_request["input"] = request.input
        if request.previous_response_id:
            api_request["previous_response_id"] = request.previous_response_id
        if request.instructions:
            api_request["instructions"] = request.instructions
        if request.tools:
            api_request["tools"] = self._normalize_tools(request.tools)
        if request.tool_choice is not None:
            api_request["tool_choice"] = request.tool_choice
        if request.parallel_tool_calls is not None:
            api_request["parallel_tool_calls"] = request.parallel_tool_calls
        if request.store is not None:
            api_request["store"] = request.store
        if request.background is not None:
            api_request["background"] = request.background
        if request.reasoning:
            # Normalize reasoning config to support effort parameter
            if isinstance(request.reasoning, dict):
                if "level" in request.reasoning:
                    # Map level to effort for o4 models
                    level_to_effort = {"low": "low", "medium": "medium", "high": "high"}
                    api_request["reasoning"] = {"effort": level_to_effort.get(request.reasoning["level"], "medium")}
                else:
                    api_request["reasoning"] = request.reasoning
        if request.include:
            api_request["include"] = request.include
        if request.temperature is not None:
            api_request["temperature"] = request.temperature
        if request.top_p is not None:
            api_request["top_p"] = request.top_p
        if request.max_output_tokens is not None:
            api_request["max_output_tokens"] = request.max_output_tokens
        if request.truncation:
            api_request["truncation"] = request.truncation
        if request.metadata:
            api_request["metadata"] = request.metadata
        if request.response_format:
            api_request["response_format"] = request.response_format
        if request.n is not None:
            api_request["n"] = request.n
        if request.presence_penalty is not None:
            api_request["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty is not None:
            api_request["frequency_penalty"] = request.frequency_penalty
        if request.timeout is not None:
            api_request["timeout"] = request.timeout
        
        # Make the API call to Responses API
        try:
            response = await self.client.responses.create(**api_request)
        except AttributeError as e:
            # SDK doesn't have responses API - this shouldn't happen with pinned version
            logger.error(f"SDK missing responses API: {e}")
            raise RuntimeError(
                f"OpenAI SDK {openai.__version__} does not support Responses API. "
                "This is unexpected with the pinned version."
            )
        except Exception as e:
            # Handle specific errors
            if hasattr(e, 'status_code') and e.status_code == 404:
                # Model not found
                raise ValueError(
                    f"Model '{actual_model}' not found. "
                    f"The gateway mapped '{request.model}' to '{actual_model}'. "
                    "Please check model availability."
                )
            logger.error(f"Error calling OpenAI Responses API: {e}")
            raise
        
        # Convert OpenAI response to our response model
        # The response from OpenAI SDK may have different structure
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response
        
        # Normalize the response to handle different SDK versions
        response_dict = self._normalize_response(response_dict)
        
        # Extract tool calls from choices if present
        tool_calls = None
        if 'choices' in response_dict and response_dict['choices']:
            first_choice = response_dict['choices'][0]
            if 'message' in first_choice and 'tool_calls' in first_choice['message']:
                tool_calls = first_choice['message']['tool_calls']
        
        # Build output array format for Responses API
        output = None
        if 'choices' in response_dict and response_dict['choices']:
            output = []
            for choice in response_dict['choices']:
                if 'message' in choice:
                    msg = choice['message']
                    output_item = {
                        "role": msg.get("role", "assistant"),
                        "content": msg.get("content")
                    }
                    if msg.get("tool_calls"):
                        output_item["tool_calls"] = msg["tool_calls"]
                    output.append(output_item)
        elif response_dict.get('output'):
            output = response_dict['output']
        
        # Extract usage information
        usage = response_dict.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)
        reasoning_tokens = usage.get('reasoning_tokens', 0)
        
        return ResponseObject(
            id=response_dict.get('id', ''),
            object=response_dict.get('object', 'response'),
            created=response_dict.get('created', 0),
            model=response_dict.get('model', ''),
            output=output,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            tool_calls=tool_calls or response_dict.get('tool_calls'),
            status=response_dict.get('status', 'completed'),
            incomplete_details=response_dict.get('incomplete_details'),
            choices=response_dict.get('choices'),
            data=response_dict.get('data'),
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": input_tokens + output_tokens + reasoning_tokens
            }
        )
    
    async def stream_response(self, request: ResponseRequest) -> AsyncIterator[str]:
        """Stream a response"""
        request.stream = True
        
        # Get the actual model name from config
        from ..config import settings
        model_config = settings.model_mapping.get(request.model, {})
        actual_model = model_config.get("model", request.model)
        
        # Build the API request (same as create_response)
        api_request = {
            "model": actual_model,
            "stream": True
        }
        
        # Add all optional fields
        if request.input is not None:
            api_request["input"] = request.input
        if request.previous_response_id:
            api_request["previous_response_id"] = request.previous_response_id
        if request.instructions:
            api_request["instructions"] = request.instructions
        if request.tools:
            api_request["tools"] = self._normalize_tools(request.tools)
        if request.tool_choice is not None:
            api_request["tool_choice"] = request.tool_choice
        if request.parallel_tool_calls is not None:
            api_request["parallel_tool_calls"] = request.parallel_tool_calls
        if request.store is not None:
            api_request["store"] = request.store
        if request.background is not None:
            api_request["background"] = request.background
        if request.reasoning:
            # Normalize reasoning config to support effort parameter
            if isinstance(request.reasoning, dict):
                if "level" in request.reasoning:
                    # Map level to effort for o4 models
                    level_to_effort = {"low": "low", "medium": "medium", "high": "high"}
                    api_request["reasoning"] = {"effort": level_to_effort.get(request.reasoning["level"], "medium")}
                else:
                    api_request["reasoning"] = request.reasoning
        if request.include:
            api_request["include"] = request.include
        if request.temperature is not None:
            api_request["temperature"] = request.temperature
        if request.top_p is not None:
            api_request["top_p"] = request.top_p
        if request.max_output_tokens is not None:
            api_request["max_output_tokens"] = request.max_output_tokens
        if request.truncation:
            api_request["truncation"] = request.truncation
        if request.metadata:
            api_request["metadata"] = request.metadata
        if request.response_format:
            api_request["response_format"] = request.response_format
        if request.n is not None:
            api_request["n"] = request.n
        if request.presence_penalty is not None:
            api_request["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty is not None:
            api_request["frequency_penalty"] = request.frequency_penalty
        
        # Stream the response using Responses API
        try:
            stream = await self.client.responses.create(**api_request)
        except AttributeError as e:
            logger.error(f"SDK missing responses API for streaming: {e}")
            raise RuntimeError(
                f"OpenAI SDK {openai.__version__} does not support Responses API streaming. "
                "This is unexpected with the pinned version."
            )
        except Exception as e:
            # Handle specific errors
            if hasattr(e, 'status_code') and e.status_code == 404:
                raise ValueError(
                    f"Model '{actual_model}' not found for streaming. "
                    f"The gateway mapped '{request.model}' to '{actual_model}'."
                )
            logger.error(f"Error calling OpenAI streaming API: {e}")
            raise
        
        async for chunk in stream:
            # Handle different chunk formats
            if hasattr(chunk, 'model_dump'):
                chunk_dict = chunk.model_dump()
            elif isinstance(chunk, dict):
                chunk_dict = chunk
            else:
                chunk_dict = {
                    "type": getattr(chunk, 'type', 'unknown'),
                    "delta": getattr(chunk, 'delta', None),
                    "data": getattr(chunk, 'data', None),
                    "id": getattr(chunk, 'id', None),
                    "created": getattr(chunk, 'created', None)
                }
            yield json.dumps(chunk_dict)
    
    async def retrieve_response(self, response_id: str) -> ResponseObject:
        """Retrieve a stored response"""
        try:
            response = await self.client.responses.retrieve(response_id)
        except AttributeError as e:
            logger.error(f"SDK missing responses.retrieve: {e}")
            raise RuntimeError(
                f"OpenAI SDK {openai.__version__} does not support response retrieval. "
                "This is unexpected with the pinned version."
            )
        except Exception as e:
            if hasattr(e, 'status_code') and e.status_code == 404:
                raise ValueError(f"Response '{response_id}' not found")
            logger.error(f"Error retrieving response: {e}")
            raise
        
        # The SDK object may not support model_dump in older versions
        response_dict = response.model_dump() if hasattr(response, 'model_dump') else response.__dict__

        # Normalize to account for possible beta format changes
        response_dict = self._normalize_response(response_dict)

        # Build usage dict with sensible defaults
        usage = response_dict.get('usage', {})
        input_tokens = usage.get('prompt_tokens', response_dict.get('input_tokens', 0))
        output_tokens = usage.get('completion_tokens', response_dict.get('output_tokens', 0))
        reasoning_tokens = usage.get('reasoning_tokens', response_dict.get('reasoning_tokens', 0))

        # Attempt to extract assistant tool calls if embedded in choices
        tool_calls = response_dict.get('tool_calls')
        if not tool_calls and response_dict.get('choices'):
            first_choice = response_dict['choices'][0]
            if isinstance(first_choice, dict):
                message = first_choice.get('message') or {}
                tool_calls = message.get('tool_calls')

        return ResponseObject(
            id=response_dict.get('id', response_id),
            object=response_dict.get('object', 'response'),
            created=response_dict.get('created', 0),
            model=response_dict.get('model', ''),
            output=response_dict.get('output'),
            # No standalone output_text field; callers should inspect `output`
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            tool_calls=tool_calls,
            status=response_dict.get('status'),
            incomplete_details=response_dict.get('incomplete_details'),
            choices=response_dict.get('choices'),
            data=response_dict.get('data'),
            usage={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "total_tokens": input_tokens + output_tokens + reasoning_tokens,
            },
        )
    
    async def delete_response(self, response_id: str) -> dict:
        """Delete a stored response"""
        try:
            result = await self.client.responses.delete(response_id)
            return {"id": response_id, "deleted": True}
        except AttributeError as e:
            logger.error(f"SDK missing responses.delete: {e}")
            raise RuntimeError(
                f"OpenAI SDK {openai.__version__} does not support response deletion. "
                "This is unexpected with the pinned version."
            )
        except Exception as e:
            if hasattr(e, 'status_code') and e.status_code == 404:
                raise ValueError(f"Response '{response_id}' not found")
            logger.error(f"Error deleting response: {e}")
            raise
