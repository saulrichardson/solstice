#!/usr/bin/env python3
"""
Check if the OpenAI SDK supports the Responses API.
Run this before starting the gateway to ensure compatibility.
"""
import sys

try:
    import openai
    from openai import AsyncOpenAI
    
    print(f"OpenAI SDK version: {openai.__version__}")
    
    # Check for Responses API support
    client = AsyncOpenAI(api_key="dummy-key-for-testing")
    
    if hasattr(client, 'responses'):
        print("✓ SDK supports Responses API")
        
        # Check for required methods
        required_methods = ['create', 'retrieve', 'delete']
        missing = []
        
        for method in required_methods:
            if not hasattr(client.responses, method):
                missing.append(method)
        
        if missing:
            print(f"✗ Missing methods: {', '.join(missing)}")
            print("Please upgrade to a newer version of the OpenAI SDK")
            sys.exit(1)
        else:
            print("✓ All required methods are available")
            sys.exit(0)
    else:
        print("✗ SDK does not support Responses API")
        print("Please upgrade to openai>=1.50.0")
        sys.exit(1)
        
except ImportError:
    print("✗ OpenAI SDK not installed")
    print("Run: pip install openai>=1.50.0")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error checking SDK: {e}")
    sys.exit(1)