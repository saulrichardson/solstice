"""Model capabilities and requirements configuration.

This module defines the capabilities and requirements for different LLM models,
allowing the system to automatically adapt requests based on the model being used.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class ModelCapabilities:
    """Defines capabilities and requirements for a specific model."""
    
    # Vision capabilities
    supports_vision: bool = False
    vision_requires_tools: bool = False
    vision_tool_config: Optional[Dict[str, Any]] = None
    
    # Parameter support
    supports_temperature: bool = True
    supports_temperature_with_vision: bool = True
    
    # Response format
    response_format: str = "standard"  # "standard" or "o4-mini"
    
    # Other capabilities
    supports_reasoning: bool = False
    max_context_length: Optional[int] = None
    
    # Default parameters
    default_temperature: float = 0.0
    default_max_tokens: int = 4096


# Model-specific capabilities
MODEL_CAPABILITIES: Dict[str, ModelCapabilities] = {
    "gpt-4.1": ModelCapabilities(
        supports_vision=True,
        supports_temperature=True,
        supports_temperature_with_vision=True,
        response_format="standard",
    ),
    
    "gpt-4.1-mini": ModelCapabilities(
        supports_vision=False,
        supports_temperature=True,
        response_format="standard",
    ),
    
    "o4-mini": ModelCapabilities(
        supports_vision=True,
        vision_requires_tools=True,
        vision_tool_config={
            "type": "code_interpreter",
            "container": {"type": "auto"}
        },
        supports_temperature=True,
        supports_temperature_with_vision=False,  # Key limitation!
        response_format="o4-mini",
        supports_reasoning=True,
    ),
    
    "gpt-4o": ModelCapabilities(
        supports_vision=True,
        supports_temperature=True,
        supports_temperature_with_vision=True,
        response_format="standard",
    ),
    
    "gpt-4o-mini": ModelCapabilities(
        supports_vision=True,
        supports_temperature=True,
        supports_temperature_with_vision=True,
        response_format="standard",
    ),
}


def get_model_capabilities(model: str) -> ModelCapabilities:
    """Get capabilities for a specific model.
    
    Args:
        model: Model name
        
    Returns:
        ModelCapabilities for the model, or default capabilities if not found
    """
    # Default to gpt-4.1 capabilities if model not found
    return MODEL_CAPABILITIES.get(model, MODEL_CAPABILITIES["gpt-4.1"])


def build_vision_request(
    model: str,
    text_prompt: str,
    image_data_uri: str,
    max_output_tokens: int = 1000,
    temperature: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """Build a vision request based on model capabilities.
    
    Args:
        model: Model name
        text_prompt: Text prompt for the image
        image_data_uri: Base64 encoded image data URI
        max_output_tokens: Maximum output tokens
        temperature: Temperature (if None, uses model default)
        **kwargs: Additional parameters
        
    Returns:
        Request dictionary configured for the specific model
    """
    capabilities = get_model_capabilities(model)
    
    # Base request
    request = {
        "model": model,
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": text_prompt},
                {"type": "input_image", "image_url": image_data_uri}
            ]
        }],
        "max_output_tokens": max_output_tokens,
        **kwargs
    }
    
    # Add tools if required for vision
    if capabilities.vision_requires_tools and capabilities.vision_tool_config:
        request["tools"] = [capabilities.vision_tool_config]
    
    # Add temperature if supported
    if temperature is None:
        temperature = capabilities.default_temperature
    
    if capabilities.supports_temperature_with_vision:
        request["temperature"] = temperature
    elif temperature is not None and capabilities.supports_temperature:
        # Model supports temperature but not with vision
        # Don't add temperature parameter
        pass
    
    return request


def extract_text_from_response(response: Dict[str, Any], model: str) -> str:
    """Extract text from response based on model format.
    
    Args:
        response: Response dictionary
        model: Model name
        
    Returns:
        Extracted text content
        
    Raises:
        ValueError: If response format is invalid
    """
    capabilities = get_model_capabilities(model)
    
    if capabilities.response_format == "o4-mini":
        # o4-mini format: reasoning output followed by message
        return _extract_o4_mini_text(response)
    else:
        # Standard format
        return _extract_standard_text(response)


def _extract_o4_mini_text(response: Dict[str, Any]) -> str:
    """Extract text from o4-mini response format."""
    if not isinstance(response.get("output"), list) or not response["output"]:
        raise ValueError("Invalid response format: 'output' must be a non-empty list")
    
    # Find the message output (skip reasoning outputs)
    for output in response["output"]:
        if output.get("type") == "message" and isinstance(output.get("content"), list):
            for content_item in output["content"]:
                if content_item.get("type") == "output_text" and "text" in content_item:
                    return content_item["text"]
    
    raise ValueError("No message output found in o4-mini response")


def _extract_standard_text(response: Dict[str, Any]) -> str:
    """Extract text from standard response format."""
    if not isinstance(response.get("output"), list) or not response["output"]:
        raise ValueError("Invalid response format: 'output' must be a non-empty list")
    
    output = response["output"][0]
    if not isinstance(output.get("content"), list) or not output["content"]:
        raise ValueError("Invalid response format: 'output[0].content' must be a non-empty list")
    
    content = output["content"][0]
    if "text" not in content:
        raise ValueError("Invalid response format: 'output[0].content[0].text' not found")
    
    return content["text"]