#!/usr/bin/env python3
"""Check available models through the gateway."""

import httpx
import os

# Check what models are available
gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8080")

print("Checking available models at gateway...")
print(f"Gateway URL: {gateway_url}")
print("-" * 80)

# Try to list models (if the gateway supports it)
try:
    response = httpx.get(f"{gateway_url}/v1/models")
    if response.status_code == 200:
        models = response.json()
        print("Available models:")
        for model in models.get("data", []):
            print(f"  - {model.get('id', 'unknown')}")
    else:
        print(f"Models endpoint returned: {response.status_code}")
except Exception as e:
    print(f"Could not list models: {e}")

# Test specific models directly
print("\nTesting specific models...")
test_models = ["gpt-4.1", "gpt-4.1-mini", "o4-mini", "o1-mini", "gpt-4o", "gpt-4o-mini"]

for model in test_models:
    try:
        response = httpx.post(
            f"{gateway_url}/v1/responses",
            json={
                "model": model,
                "input": [{"role": "user", "content": [{"type": "input_text", "text": "test"}]}]
            },
            timeout=10.0
        )
        if response.status_code == 200:
            print(f"✅ {model:<15} - Available")
        else:
            print(f"❌ {model:<15} - Status {response.status_code}")
    except Exception as e:
        print(f"❌ {model:<15} - Error: {str(e)[:50]}")