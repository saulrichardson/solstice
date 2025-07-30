#!/usr/bin/env python3
"""Simple test for image analysis with ResponsesClient."""

import asyncio
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.fact_check.core.responses_client import ResponsesClient

async def test_image_with_responses_api():
    """Test image analysis using Responses API directly."""
    
    # Setup
    client = ResponsesClient()
    
    # Find a test image
    image_path = Path("data/cache/FlublokPI/extracted/figures/table_p1_f8743488.png")
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    data_uri = f"data:image/png;base64,{image_base64}"
    
    print(f"Testing with image: {image_path.name}")
    print(f"Image size: {len(image_data)} bytes")
    print(f"Base64 size: {len(image_base64)} chars")
    print("-" * 80)
    
    # Test with gpt-4.1 first (known to work)
    try:
        print("Testing with gpt-4.1...")
        response = await client.create_response(
            model="gpt-4.1",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "What type of image is this? Describe briefly."},
                    {"type": "input_image", "image_url": data_uri}
                ]
            }],
            temperature=0.0,
            max_output_tokens=200
        )
        
        text = client.extract_text(response)
        print(f"Response: {text}")
        print("✅ gpt-4.1 vision test passed")
        
    except Exception as e:
        print(f"❌ gpt-4.1 test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "-" * 80)
    
    # Test with o4-mini
    try:
        print("Testing with o4-mini...")
        response = await client.create_response(
            model="o4-mini",
            input=[{
                "role": "user", 
                "content": [
                    {"type": "input_text", "text": "What type of image is this? Describe briefly."},
                    {"type": "input_image", "image_url": data_uri}
                ]
            }],
            temperature=0.0,
            max_output_tokens=200
        )
        
        text = client.extract_text(response)
        print(f"Response: {text}")
        print("✅ o4-mini vision test passed")
        
    except Exception as e:
        print(f"❌ o4-mini test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_image_with_responses_api())