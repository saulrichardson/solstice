#!/usr/bin/env python3
"""Test OpenAI API key with standard Chat Completions API"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get the API key
api_key = os.getenv('OPENAI_API_KEY')
print(f"Testing with the same API key...")
print(f"Key: {api_key[:20]}...{api_key[-20:]}")

# Create client
client = OpenAI(api_key=api_key)

print("\nTesting OpenAI Chat Completions API...")
print("-" * 50)

try:
    # Test with standard chat completions
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Say hello"}
        ],
        max_tokens=10
    )
    
    print("Success! Response:")
    print(response.choices[0].message.content)
    
except Exception as e:
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
    
print("\n" + "-" * 50)
print("Testing models.list() endpoint...")

try:
    models = client.models.list()
    print(f"Success! Found {len(list(models))} models")
except Exception as e:
    print(f"Error: {e}")