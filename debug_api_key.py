#!/usr/bin/env python3
"""Debug why curl works but Python SDK doesn't"""

import os
import subprocess
from dotenv import load_dotenv

# Load from .env file
load_dotenv()
env_key = os.getenv('OPENAI_API_KEY')

print("Step 1: Testing curl with key from .env file")
print("-" * 60)

# Get key directly from .env file using grep
result = subprocess.run(['grep', 'OPENAI_API_KEY', '.env'], capture_output=True, text=True)
grep_key = result.stdout.strip().split('=')[1]

print(f"Key from os.getenv(): {env_key[:20]}...{env_key[-20:]}")
print(f"Key from grep:        {grep_key[:20]}...{grep_key[-20:]}")
print(f"Keys match: {env_key == grep_key}")

# Test with curl using grep key
print("\nStep 2: Testing curl with grep key")
curl_result = subprocess.run([
    'curl', '-s', 'https://api.openai.com/v1/models',
    '-H', f'Authorization: Bearer {grep_key}'
], capture_output=True, text=True)

if '"object": "list"' in curl_result.stdout:
    print("✓ Curl works with grep key!")
else:
    print("✗ Curl failed with grep key")
    print(curl_result.stdout[:200])

# Now test Python requests library instead of OpenAI SDK
print("\nStep 3: Testing with requests library")
import requests

headers = {
    'Authorization': f'Bearer {env_key}',
    'Content-Type': 'application/json'
}

response = requests.get('https://api.openai.com/v1/models', headers=headers)
print(f"Status code: {response.status_code}")
if response.status_code == 200:
    print("✓ Requests library works!")
else:
    print("✗ Requests library failed")
    print(response.json())

# Test OpenAI SDK with explicit configuration
print("\nStep 4: Testing OpenAI SDK with different configurations")
from openai import OpenAI

# Try 1: Default
try:
    client1 = OpenAI()
    client1.models.list()
    print("✓ Default OpenAI client works!")
except Exception as e:
    print(f"✗ Default client failed: {str(e)[:100]}...")

# Try 2: Explicit api_key
try:
    client2 = OpenAI(api_key=env_key)
    client2.models.list()
    print("✓ Explicit api_key works!")
except Exception as e:
    print(f"✗ Explicit api_key failed: {str(e)[:100]}...")

# Try 3: Explicit api_key from grep
try:
    client3 = OpenAI(api_key=grep_key)
    client3.models.list()
    print("✓ Grep api_key works!")
except Exception as e:
    print(f"✗ Grep api_key failed: {str(e)[:100]}...")