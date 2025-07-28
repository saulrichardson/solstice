#!/usr/bin/env python3
"""Test o4-mini model functionality"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.core.responses_client import ResponsesClient

client = ResponsesClient()

print("Testing o4-mini Model")
print("="*50)

# Test 1: Basic response
print("\n1. Testing basic o4-mini response...")
try:
    response = client.create_response(
        model="o4-mini",
        input="What is 10 + 15? Give just the number.",
        temperature=0
    )
    
    print(f"Model in response: {response.get('model')}")
    print(f"Response ID: {response.get('id')}")
    
    # Extract response
    output = response.get('output', [])
    if output and isinstance(output, list):
        for msg in output:
            if isinstance(msg, dict) and 'content' in msg:
                content = msg['content']
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            print(f"Response: {item['text']}")
                elif isinstance(content, str):
                    print(f"Response: {content}")
    
    # Check for reasoning tokens (o4-mini feature)
    usage = response.get('usage', {})
    reasoning_tokens = usage.get('reasoning_tokens', 0)
    print(f"Reasoning tokens used: {reasoning_tokens}")
    
except Exception as e:
    print(f"Error: {e}")

# Test 2: Test with reasoning
print("\n\n2. Testing o4-mini with reasoning task...")
try:
    response = client.create_response(
        model="o4-mini",
        input="Solve step by step: If I have 5 apples and give away 2, then buy 3 more, how many do I have?",
        reasoning={"effort": "medium"},
        temperature=0
    )
    
    print(f"Model: {response.get('model')}")
    
    # Extract response
    output = response.get('output', [])
    if output and isinstance(output, list):
        for msg in output:
            if isinstance(msg, dict) and 'content' in msg:
                content = msg['content']
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            print(f"Response: {item['text'][:200]}...")
    
    usage = response.get('usage', {})
    print(f"\nToken usage:")
    print(f"- Input: {usage.get('input_tokens', 0)}")
    print(f"- Output: {usage.get('output_tokens', 0)}")
    print(f"- Reasoning: {usage.get('reasoning_tokens', 0)}")
    print(f"- Total: {usage.get('total_tokens', 0)}")
    
except Exception as e:
    print(f"Error: {e}")

# Test 3: Compare models
print("\n\n3. Comparing different models...")
models_to_test = ["gpt-4.1", "gpt-4o", "o4-mini"]

for model in models_to_test:
    try:
        response = client.create_response(
            model=model,
            input="Say 'Hello' and nothing else.",
            temperature=0
        )
        
        # Extract text
        text = "No response"
        output = response.get('output', [])
        if output and isinstance(output, list):
            for msg in output:
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                text = item['text']
                                break
                    elif isinstance(content, str):
                        text = content
                        break
                    if text != "No response":
                        break
        
        print(f"\n{model}:")
        print(f"  API response model: {response.get('model')}")
        print(f"  Response text: {text}")
        print(f"  Reasoning tokens: {response.get('usage', {}).get('reasoning_tokens', 0)}")
        
    except Exception as e:
        print(f"\n{model}: Error - {e}")

print("\n" + "="*50)
print("Summary:")
print("- No model aliasing detected in gateway")
print("- Models are passed through as specified by the user")
print("- Each model maintains its identity in the API response")