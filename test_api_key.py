#!/usr/bin/env python3
"""Test OpenAI API key directly with the Responses API"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get the API key
api_key = os.getenv('OPENAI_API_KEY')
print(f"API Key length: {len(api_key) if api_key else 0}")
print(f"API Key format: {api_key[:10]}...{api_key[-10:] if api_key else 'None'}")
print(f"API Key full (for debugging): {repr(api_key)}")

# Create client
client = OpenAI(api_key=api_key)

print("\nTesting OpenAI Responses API...")
print("-" * 50)

try:
    # Test with the Responses API
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions="You are a helpful assistant.",
        input="Say hello",
        max_output_tokens=10
    )
    
    print("Success! Response:")
    print(response)
    
except Exception as e:
    print(f"Error type: {type(e).__name__}")
    print(f"Error message: {e}")
    
    # Print raw error details
    if hasattr(e, 'response'):
        print(f"\nRaw response status: {e.response.status_code}")
        print(f"Raw response headers: {dict(e.response.headers)}")
        print(f"Raw response body: {e.response.text}")