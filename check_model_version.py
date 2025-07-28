#!/usr/bin/env python3
"""Quick check to verify which model version is being used"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.core.responses_client import ResponsesClient

# Test the model
client = ResponsesClient()

response = client.create_response(
    model="gpt-4.1",
    input="What model are you? Just state your model name.",
    temperature=0
)

print(f"Response object model field: {response.get('model', 'Not specified')}")

# Extract the response text
output = response.get('output', [])
if output and isinstance(output, list):
    for msg in output:
        if isinstance(msg, dict) and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        print(f"Model's response: {item['text']}")
                        break

# Also test with a fact-checking specific prompt
print("\n--- Fact-checking test ---")
response2 = client.create_response(
    model="gpt-4.1",
    input='Return JSON: {"test": "success", "model": "gpt-4.1"}',
    temperature=0
)

print(f"Fact-check response model: {response2.get('model', 'Not specified')}")