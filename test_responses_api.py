#!/usr/bin/env python3
"""Test script to verify the Responses API implementation works correctly."""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.injestion.agent.llm_client import call_llm, _call_llm_async
from src.gateway.app.config import settings

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_simple_text():
    """Test simple text input with Responses API."""
    print("\n1. Testing simple text input...")
    try:
        response = await _call_llm_async(
            system_prompt="You are a helpful assistant. Respond with valid JSON.",
            user_content="What is 2+2? Respond with JSON: {\"answer\": <number>}",
            model="gpt-4.1",
            temperature=0.1,
        )
        print(f"Response: {response}")
        # Try to parse as JSON
        parsed = json.loads(response)
        print(f"Parsed JSON: {parsed}")
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def test_multimodal_input():
    """Test multimodal input (text + image) with Responses API."""
    print("\n2. Testing multimodal input...")
    try:
        # Create a test input with text and image blocks
        user_content = [
            {"type": "text", "text": "Describe this image in JSON format: {\"description\": \"...\"}"},
            {
                "type": "input_image", 
                "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/200px-Cat03.jpg"
            }
        ]
        
        response = await _call_llm_async(
            system_prompt="You are an image analyst. Always respond with valid JSON.",
            user_content=user_content,
            model="gpt-4.1",
            temperature=0.1,
        )
        print(f"Response: {response}")
        # Try to parse as JSON
        parsed = json.loads(response)
        print(f"Parsed JSON: {parsed}")
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


def test_sync_wrapper():
    """Test the synchronous wrapper."""
    print("\n3. Testing synchronous wrapper...")
    try:
        response = call_llm(
            system_prompt="You are a helpful assistant. Respond with valid JSON.",
            user_content="What is the capital of France? Respond with JSON: {\"capital\": \"...\"}",
            model="gpt-4.1",
            temperature=0.1,
        )
        print(f"Response: {response}")
        # Try to parse as JSON
        parsed = json.loads(response)
        print(f"Parsed JSON: {parsed}")
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all tests."""
    print("Testing Responses API implementation...")
    print(f"API Key configured: {'Yes' if settings.openai_api_key else 'No'}")
    
    results = []
    
    # Test 1: Simple text
    results.append(await test_simple_text())
    
    # Test 2: Multimodal input
    results.append(await test_multimodal_input())
    
    # Test 3: Sync wrapper
    results.append(test_sync_wrapper())
    
    # Summary
    print("\n" + "="*50)
    print("Test Results:")
    print(f"Simple text input: {'✓ PASSED' if results[0] else '✗ FAILED'}")
    print(f"Multimodal input: {'✓ PASSED' if results[1] else '✗ FAILED'}")
    print(f"Synchronous wrapper: {'✓ PASSED' if results[2] else '✗ FAILED'}")
    print(f"\nOverall: {sum(results)}/{len(results)} tests passed")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())