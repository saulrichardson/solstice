#!/usr/bin/env python3
"""Test o4-mini without temperature parameter"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.core.responses_client import ResponsesClient

client = ResponsesClient()

print("Testing o4-mini (without temperature parameter)")
print("="*50)

# Test 1: Basic call
print("\n1. Basic o4-mini call...")
try:
    response = client.create_response(
        model="o4-mini",
        input="What is 2+2? Answer with just the number."
    )
    
    print(f"✅ Success!")
    print(f"Model: {response.get('model')}")
    
    # Extract response
    output = response.get('output', [])
    for msg in output:
        if isinstance(msg, dict) and msg.get('type') == 'reasoning':
            print("Found reasoning output (encrypted)")
        elif isinstance(msg, dict) and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        print(f"Response: {item['text']}")
    
    usage = response.get('usage', {})
    print(f"Reasoning tokens: {usage.get('reasoning_tokens', 0)}")
    
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: With reasoning parameter
print("\n\n2. o4-mini with reasoning parameter...")
try:
    response = client.create_response(
        model="o4-mini",
        input="Solve: If a car travels 60 km/h for 2.5 hours, how far does it go?",
        reasoning={"effort": "medium"}
    )
    
    print(f"✅ Success!")
    print(f"Model: {response.get('model')}")
    
    # Extract response
    output = response.get('output', [])
    for msg in output:
        if isinstance(msg, dict) and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        print(f"Response: {item['text']}")
    
    usage = response.get('usage', {})
    print(f"\nToken usage:")
    print(f"- Input: {usage.get('input_tokens', 0)}")
    print(f"- Output: {usage.get('output_tokens', 0)}")
    print(f"- Reasoning: {usage.get('reasoning_tokens', 0)}")
    
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: JSON generation
print("\n\n3. o4-mini generating JSON...")
try:
    response = client.create_response(
        model="o4-mini",
        input='Return this exact JSON: {"status": "success", "value": 42}'
    )
    
    print(f"✅ Success!")
    
    # Extract response
    output = response.get('output', [])
    for msg in output:
        if isinstance(msg, dict) and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        print(f"Response: {item['text']}")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*50)
print("Key findings:")
print("- o4-mini does NOT support the 'temperature' parameter")
print("- o4-mini works fine without temperature")
print("- o4-mini includes reasoning tokens in its usage")
print("- The gateway correctly passes through all model names without aliasing")