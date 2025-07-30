#!/usr/bin/env python3
"""Debug o4-mini vision issues."""

import asyncio
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.fact_check.core.responses_client import ResponsesClient

async def debug_o4_mini():
    """Run through debugging steps for o4-mini vision."""
    
    client = ResponsesClient()
    
    print("=" * 80)
    print("O4-MINI VISION DEBUGGING")
    print("=" * 80)
    
    # Test 1: Text-only with o4-mini
    print("\n1. Testing o4-mini with text-only...")
    try:
        response = await client.create_response(
            model="o4-mini",
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": "ping"}
            ]}],
            temperature=0.0
        )
        text = client.extract_text(response)
        print(f"✅ Text-only works: {text[:100]}")
    except Exception as e:
        print(f"❌ Text-only failed: {e}")
        return
    
    # Test 2: Try different model aliases
    print("\n2. Testing different o4-mini aliases...")
    aliases = ["o4-mini", "o4-mini-2025-07-18", "o4-mini-vision-2025-06-26"]
    
    for alias in aliases:
        try:
            response = await client.create_response(
                model=alias,
                input=[{"role": "user", "content": [
                    {"type": "input_text", "text": "test"}
                ]}],
                temperature=0.0
            )
            print(f"✅ {alias} works")
        except Exception as e:
            print(f"❌ {alias} failed: {str(e)[:100]}")
    
    # Test 3: Small image without tools
    print("\n3. Testing o4-mini with small image (no tools)...")
    
    # Create a tiny test image (1x1 white pixel PNG)
    tiny_png = base64.b64encode(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
        b'\x00\x01\x01\x00\x05\x00\x00\x00\x00IEND\xaeB`\x82'
    ).decode()
    
    try:
        response = await client.create_response(
            model="o4-mini",
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": "What is this image?"},
                {"type": "input_image", "image_url": f"data:image/png;base64,{tiny_png}"}
            ]}],
            temperature=0.0
        )
        print("✅ Small image works without tools")
    except Exception as e:
        print(f"❌ Small image failed: {e}")
        
        # Test 4: With tools enabled
        print("\n4. Testing o4-mini with image + tools...")
        try:
            response = await client.create_response(
                model="o4-mini",
                tools=[{"type": "python"}],  # Enable Code Interpreter
                input=[{"role": "user", "content": [
                    {"type": "input_text", "text": "What is this image?"},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{tiny_png}"}
                ]}],
                temperature=0.0
            )
            print("✅ Image works WITH tools enabled!")
            text = client.extract_text(response)
            print(f"Response: {text[:200]}")
        except Exception as e:
            print(f"❌ Image + tools also failed: {e}")
    
    # Test 5: Check actual image size
    print("\n5. Checking actual image sizes...")
    image_path = Path("data/cache/FlublokPI/extracted/figures/table_p1_f8743488.png")
    if image_path.exists():
        image_size = image_path.stat().st_size
        base64_size = (image_size * 4) // 3  # Rough estimate
        print(f"Image size: {image_size:,} bytes ({image_size/1024/1024:.1f} MB)")
        print(f"Base64 size estimate: {base64_size:,} bytes ({base64_size/1024/1024:.1f} MB)")
        
        if base64_size > 8 * 1024 * 1024:
            print("⚠️  Image might exceed o4-mini's 8MB limit")
        else:
            print("✅ Image size within limits")

if __name__ == "__main__":
    asyncio.run(debug_o4_mini())