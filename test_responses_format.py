#!/usr/bin/env python3
"""Test the correct format for OpenAI Responses API"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

print("Testing different input formats for Responses API...")
print("-" * 60)

# Test 1: Simple string input
try:
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions="You are a helpful assistant.",
        input="Say hello",
        max_output_tokens=10
    )
    print("✓ String input works!")
except Exception as e:
    print(f"✗ String input failed: {str(e)[:100]}...")

# Test 2: Message format
try:
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions="You are a helpful assistant.",
        input=[{"type": "message", "content": "Say hello"}],
        max_output_tokens=10
    )
    print("✓ Message format works!")
except Exception as e:
    print(f"✗ Message format failed: {str(e)[:100]}...")

# Test 3: Text format (what the code is using)
try:
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions="You are a helpful assistant.",
        input=[{"type": "text", "text": "Say hello"}],
        max_output_tokens=10
    )
    print("✓ Text format works!")
except Exception as e:
    print(f"✗ Text format failed: {str(e)[:100]}...")

# Test 4: With image_url (for vision)
try:
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions="You are a helpful assistant.",
        input=[
            {"type": "message", "content": "What's in this image?"},
            {"type": "image_url", "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}
        ],
        max_output_tokens=10
    )
    print("✓ Image with message works!")
except Exception as e:
    print(f"✗ Image with message failed: {str(e)[:100]}...")