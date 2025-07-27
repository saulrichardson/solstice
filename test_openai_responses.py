#!/usr/bin/env python3
"""Test if OpenAI SDK has responses API."""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from openai import AsyncOpenAI, OpenAI
from src.gateway.app.config import settings

# Check what methods are available
client = OpenAI(api_key=settings.openai_api_key)
async_client = AsyncOpenAI(api_key=settings.openai_api_key)

print("OpenAI client attributes:")
print([attr for attr in dir(client) if not attr.startswith('_')])

print("\nAsyncOpenAI client attributes:")
print([attr for attr in dir(async_client) if not attr.startswith('_')])

# Check if responses exists
print(f"\nHas 'responses' attribute: {hasattr(client, 'responses')}")
print(f"Has 'chat' attribute: {hasattr(client, 'chat')}")
print(f"Has 'completions' attribute: {hasattr(client, 'completions')}")

# If responses exists, check its methods
if hasattr(client, 'responses'):
    print("\nResponses methods:")
    print([attr for attr in dir(client.responses) if not attr.startswith('_')])