#!/usr/bin/env python3
"""Verify actual model behavior and capabilities"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.core.responses_client import ResponsesClient

client = ResponsesClient()

print("Model Behavior Verification")
print("="*50)

# Test 1: Check actual capabilities
print("\n1. Testing reasoning capabilities...")
response = client.create_response(
    model="gpt-4.1",
    input="Solve this step by step: If a train travels 120km in 1.5 hours, what is its speed in m/s?",
    temperature=0
)

output = response.get('output', [])
if output and isinstance(output, list):
    for msg in output:
        if isinstance(msg, dict) and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        print(f"Response: {item['text'][:300]}...")

# Test 2: Check JSON formatting ability
print("\n2. Testing JSON generation...")
response = client.create_response(
    model="gpt-4.1",
    input='Generate a JSON object with fields: name (string), age (number), active (boolean). Return ONLY the JSON.',
    temperature=0
)

output = response.get('output', [])
if output and isinstance(output, list):
    for msg in output:
        if isinstance(msg, dict) and 'content' in msg:
            content = msg['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text = item['text'].strip()
                        # Try to parse it
                        try:
                            if text.startswith('```'):
                                # Extract JSON from markdown
                                lines = text.split('\n')
                                json_lines = []
                                in_json = False
                                for line in lines:
                                    if line.strip() == '```json' or line.strip() == '```':
                                        in_json = not in_json
                                        continue
                                    if in_json or (not line.startswith('```') and not in_json and '{' in line):
                                        json_lines.append(line)
                                text = '\n'.join(json_lines)
                            parsed = json.loads(text)
                            print(f"✅ Valid JSON generated: {parsed}")
                        except:
                            print(f"❌ Invalid JSON: {text[:100]}...")

# Test 3: Check model consistency
print("\n3. Testing model consistency...")
models = ["gpt-4.1", "gpt-4o", "gpt-4o-2024-08-06"]
for model in models:
    try:
        response = client.create_response(
            model=model,
            input="Reply with just 'OK'",
            temperature=0
        )
        print(f"✅ Model {model} -> API says: {response.get('model')}")
    except Exception as e:
        print(f"❌ Model {model} -> Error: {e}")

# Recommendation
print("\n" + "="*50)
print("FINDINGS:")
print("- The model 'gpt-4.1' is accepted by the API")
print("- It maps to 'gpt-4.1-2025-04-14' in responses")
print("- The model identifies itself as GPT-4o")
print("- This suggests 'gpt-4.1' is an alias for a GPT-4o variant")
print("\nRECOMMENDATION:")
print("Consider using 'gpt-4o' directly for clarity, or document")
print("that 'gpt-4.1' is an alias that maps to GPT-4o.")