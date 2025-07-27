#!/usr/bin/env python3
"""Test API key by comparing curl vs Python SDK"""

import os
import subprocess
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

print("Testing with curl first...")
print("-" * 50)

# Test with curl
curl_cmd = [
    'curl', '-s', 'https://api.openai.com/v1/chat/completions',
    '-H', f'Authorization: Bearer {api_key}',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps({
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10
    })
]

result = subprocess.run(curl_cmd, capture_output=True, text=True)
response = json.loads(result.stdout)

if 'error' in response:
    print(f"Curl Error: {response['error']}")
else:
    print(f"Curl Success: {response['choices'][0]['message']['content']}")

print("\nTesting with Python SDK...")
print("-" * 50)

# Now test with SDK using exact same parameters
client = OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=10
    )
    print(f"SDK Success: {response.choices[0].message.content}")
except Exception as e:
    print(f"SDK Error: {e}")
    
# Also test the responses API with curl
print("\nTesting Responses API with curl...")
print("-" * 50)

curl_responses_cmd = [
    'curl', '-s', 'https://api.openai.com/v1/responses',
    '-H', f'Authorization: Bearer {api_key}',
    '-H', 'Content-Type: application/json',
    '-d', json.dumps({
        "model": "gpt-4o-mini",
        "instructions": "You are a helpful assistant",
        "input": "Say hello",
        "max_output_tokens": 10
    })
]

result = subprocess.run(curl_responses_cmd, capture_output=True, text=True)
if result.stdout:
    response = json.loads(result.stdout)
    if 'error' in response:
        print(f"Responses API Error: {response['error']}")
    else:
        print(f"Responses API Success!")
else:
    print(f"No response from Responses API")