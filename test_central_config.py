#!/usr/bin/env python3
"""Test that all API clients use the central configuration."""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# First, let's test with shell env var set (should be ignored by our central config)
os.environ['OPENAI_API_KEY'] = 'sk-shell-key-should-be-ignored'

from src.gateway.app.openai_client import (
    get_openai_api_key, 
    get_async_openai_client,
    validate_api_key,
    OpenAIClientError
)

print("Testing centralized OpenAI configuration...")
print("="*50)

# Test 1: Check that we get the API key from settings, not shell
try:
    api_key = get_openai_api_key()
    print(f"✓ API key loaded from settings")
    print(f"  First 10 chars: {api_key[:10]}...")
    print(f"  Last 4 chars: ...{api_key[-4:]}")
    
    # Verify it's NOT the shell key
    if api_key == os.environ['OPENAI_API_KEY']:
        print("✗ ERROR: Using shell API key instead of .env!")
    else:
        print("✓ Correctly ignoring shell OPENAI_API_KEY")
except OpenAIClientError as e:
    print(f"✗ Failed to load API key: {e}")

# Test 2: Validate API key format
print("\nValidating API key format...")
if validate_api_key():
    print("✓ API key format is valid")
else:
    print("✗ API key format is invalid")

# Test 3: Check client instantiation
print("\nTesting client instantiation...")
try:
    client = get_async_openai_client()
    print("✓ AsyncOpenAI client created successfully")
    
    # Verify the client is using our API key, not the shell one
    if hasattr(client, 'api_key') and client.api_key == os.environ['OPENAI_API_KEY']:
        print("✗ ERROR: Client using shell API key!")
    else:
        print("✓ Client configured correctly")
except Exception as e:
    print(f"✗ Failed to create client: {e}")

# Test 4: Import all modules to ensure they use central config
print("\nVerifying all modules use central config...")
try:
    # These imports should all work without issues
    from src.injestion.agent.llm_client import _CLIENT as ingestion_client
    from src.injestion.agent.llm_client_chat import _CLIENT as chat_client
    from src.gateway.app.providers.openai_provider import OpenAIProvider
    
    print("✓ All modules imported successfully")
    
    # Verify they're all using the same client instance (singleton)
    if ingestion_client is chat_client:
        print("✓ Clients are properly sharing singleton instance")
    else:
        print("✗ WARNING: Clients not sharing singleton instance")
        
except Exception as e:
    print(f"✗ Import error: {e}")

print("\n" + "="*50)
print("Central configuration test complete!")

# Cleanup
del os.environ['OPENAI_API_KEY']