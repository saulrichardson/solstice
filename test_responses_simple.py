#!/usr/bin/env python3
"""Simple test of the Responses API without async complications."""

import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from openai import AsyncOpenAI
from src.gateway.app.config import settings


async def test_basic_responses_api():
    """Test basic Responses API call."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    print("Testing basic Responses API call...")
    try:
        response = await client.responses.create(
            model="gpt-4o-mini",  # Try with a known model first
            instructions="You are a helpful assistant. Always respond with valid JSON.",
            input="What is 2+2? Respond with JSON: {\"answer\": <number>}",
            temperature=0.1,
        )
        
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        
        # Try different ways to get the output
        if hasattr(response, 'output'):
            print(f"response.output: {response.output}")
        if hasattr(response, 'text'):
            print(f"response.text: {response.text}")
        if hasattr(response, 'content'):
            print(f"response.content: {response.content}")
            
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def test_multimodal_responses():
    """Test multimodal input with Responses API."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    print("\nTesting multimodal Responses API call...")
    try:
        # Based on the docs, format should be like chat messages
        input_data = [
            {"role": "user", "content": "What teams are playing in this photo?"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/200px-Cat03.jpg"
                    }
                ]
            }
        ]
        
        response = await client.responses.create(
            model="gpt-4o-mini",
            instructions="You are an image analyst.",
            input=input_data,
            temperature=0.1,
        )
        
        print(f"Response type: {type(response)}")
        if hasattr(response, 'output'):
            print(f"response.output: {response.output}")
            
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run tests."""
    print("Testing OpenAI Responses API...")
    print(f"API Key configured: {'Yes' if settings.openai_api_key else 'No'}")
    
    # Test 1
    result1 = await test_basic_responses_api()
    
    # Test 2
    result2 = await test_multimodal_responses()
    
    print("\n" + "="*50)
    print(f"Basic test: {'✓ PASSED' if result1 else '✗ FAILED'}")
    print(f"Multimodal test: {'✓ PASSED' if result2 else '✗ FAILED'}")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())