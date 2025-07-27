#!/usr/bin/env python3
"""Test the responses.create method signature."""

import inspect
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from openai import AsyncOpenAI
from src.gateway.app.config import settings

async_client = AsyncOpenAI(api_key=settings.openai_api_key)

# Get the create method
create_method = async_client.responses.create

# Inspect the method signature
sig = inspect.signature(create_method)
print("responses.create signature:")
print(sig)

# Get parameter details
print("\nParameters:")
for name, param in sig.parameters.items():
    print(f"  {name}: {param}")

# Try to get help
print("\nMethod docstring:")
print(create_method.__doc__)