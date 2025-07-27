#!/usr/bin/env python3
"""Check which API key is being loaded."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

print("Environment variables:")
print(f"Shell OPENAI_API_KEY: {os.environ.get('OPENAI_API_KEY', 'Not set')}")

# Now import settings to see what it loads
from src.gateway.app.config import settings

print(f"\nSettings openai_api_key: {settings.openai_api_key}")
print(f"First 20 chars: {settings.openai_api_key[:20] if settings.openai_api_key else 'None'}")
print(f"Last 10 chars: {settings.openai_api_key[-10:] if settings.openai_api_key else 'None'}")