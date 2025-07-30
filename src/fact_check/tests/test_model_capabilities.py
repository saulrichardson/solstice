#!/usr/bin/env python3
"""Test suite for model capabilities."""

import asyncio
import base64
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.fact_check.config.model_capabilities import (
    get_model_capabilities,
    build_vision_request,
    extract_text_from_response,
    MODEL_CAPABILITIES
)
from src.fact_check.core.responses_client import ResponsesClient


def test_model_capabilities():
    """Test model capabilities configuration."""
    print("Testing Model Capabilities Configuration")
    print("=" * 80)
    
    for model_name, capabilities in MODEL_CAPABILITIES.items():
        print(f"\n{model_name}:")
        print(f"  - Supports vision: {capabilities.supports_vision}")
        print(f"  - Vision requires tools: {capabilities.vision_requires_tools}")
        print(f"  - Supports temperature with vision: {capabilities.supports_temperature_with_vision}")
        print(f"  - Response format: {capabilities.response_format}")
    
    # Test unknown model
    unknown_caps = get_model_capabilities("unknown-model")
    print(f"\nUnknown model defaults to: gpt-4.1 capabilities")
    assert unknown_caps == MODEL_CAPABILITIES["gpt-4.1"]


def test_vision_request_builder():
    """Test vision request building for different models."""
    print("\n\nTesting Vision Request Builder")
    print("=" * 80)
    
    test_prompt = "What is in this image?"
    test_image = "data:image/png;base64,iVBORw0KGgo..."
    
    # Test each model
    test_models = ["gpt-4.1", "o4-mini"]
    
    for model in test_models:
        print(f"\n{model} request:")
        request = build_vision_request(
            model=model,
            text_prompt=test_prompt,
            image_data_uri=test_image,
            temperature=0.0
        )
        
        print(f"  - Has temperature: {'temperature' in request}")
        print(f"  - Has tools: {'tools' in request}")
        if 'tools' in request:
            print(f"  - Tool config: {request['tools']}")


def test_response_extraction():
    """Test response extraction for different formats."""
    print("\n\nTesting Response Extraction")
    print("=" * 80)
    
    # Standard format response
    standard_response = {
        "output": [{
            "content": [{
                "text": "This is the response text"
            }]
        }]
    }
    
    # o4-mini format response
    o4_mini_response = {
        "output": [
            {
                "type": "reasoning",
                "content": []
            },
            {
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": "This is the o4-mini response"
                }]
            }
        ]
    }
    
    # Test standard extraction
    text = extract_text_from_response(standard_response, "gpt-4.1")
    print(f"\nStandard format extraction: {text}")
    assert text == "This is the response text"
    
    # Test o4-mini extraction
    text = extract_text_from_response(o4_mini_response, "o4-mini")
    print(f"o4-mini format extraction: {text}")
    assert text == "This is the o4-mini response"


async def test_real_vision_requests():
    """Test real vision requests with different models."""
    print("\n\nTesting Real Vision Requests")
    print("=" * 80)
    
    # Create a tiny test image
    tiny_png = base64.b64encode(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
        b'\x00\x01\x01\x00\x05\x00\x00\x00\x00IEND\xaeB`\x82'
    ).decode()
    
    client = ResponsesClient()
    test_models = ["gpt-4.1", "o4-mini"]
    
    for model in test_models:
        print(f"\nTesting {model}:")
        
        request = build_vision_request(
            model=model,
            text_prompt="What color is this 1x1 pixel image?",
            image_data_uri=f"data:image/png;base64,{tiny_png}",
            max_output_tokens=100
        )
        
        try:
            response = await client.create_response(**request)
            text = client.extract_text(response, model)
            print(f"  ✅ Success: {text[:100]}...")
        except Exception as e:
            print(f"  ❌ Failed: {str(e)[:100]}...")


async def main():
    """Run all tests."""
    test_model_capabilities()
    test_vision_request_builder()
    test_response_extraction()
    
    # Only run real requests if gateway is available
    try:
        await test_real_vision_requests()
    except Exception as e:
        print(f"\nSkipping real request tests (gateway not available): {e}")


if __name__ == "__main__":
    asyncio.run(main())