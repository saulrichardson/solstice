#!/usr/bin/env python3
"""Test to investigate model identity discrepancy"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.core.responses_client import ResponsesClient

client = ResponsesClient()

# Test different model identifiers
models_to_test = ["gpt-4.1", "gpt-4o", "gpt-4", "gpt-4-turbo-preview"]

print("Testing Model Identity\n" + "="*50)

for model in models_to_test:
    print(f"\n--- Testing model: {model} ---")
    try:
        response = client.create_response(
            model=model,
            input="What is your exact model name and version? Be specific.",
            temperature=0
        )
        
        print(f"API response model field: {response.get('model', 'Not specified')}")
        
        # Extract the response text
        output = response.get('output', [])
        if output and isinstance(output, list):
            for msg in output:
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                print(f"Model says: {item['text'][:200]}")  # First 200 chars
                                break
                    elif isinstance(content, str):
                        print(f"Model says: {content[:200]}")
                        break
                        
    except Exception as e:
        print(f"Error: {e}")

# Also check what the gateway is actually doing
print("\n\n--- Gateway Model Mapping Test ---")
print("Testing if gateway is remapping model names...")

# Send a request with detailed logging
response = client.create_response(
    model="gpt-4.1",
    input="Return exactly: 'Model confirmed'",
    temperature=0
)

print(f"\nFull response metadata:")
print(f"Model: {response.get('model')}")
print(f"Object: {response.get('object')}")
print(f"Created: {response.get('created')}")
print(f"ID: {response.get('id')}")