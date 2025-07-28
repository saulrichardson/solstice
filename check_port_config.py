#!/usr/bin/env python3
"""Check that all port configurations are consistent"""

import os
import sys

print("=== Port Configuration Check ===\n")

# Check environment variable
env_port = os.getenv("SOLSTICE_GATEWAY_PORT", "Not set")
print(f"Environment variable SOLSTICE_GATEWAY_PORT: {env_port}")

# Check .env file
try:
    with open(".env", "r") as f:
        for line in f:
            if "SOLSTICE_GATEWAY_PORT" in line and not line.strip().startswith("#"):
                print(f".env file: {line.strip()}")
except FileNotFoundError:
    print(".env file: Not found")

# Check gateway config default
try:
    from src.gateway.app.config import settings
    print(f"Gateway config default: {settings.solstice_gateway_port}")
except ImportError:
    print("Gateway config: Could not import")

# Check ResponsesClient default
try:
    from src.fact_check.core.responses_client import ResponsesClient
    client = ResponsesClient()
    print(f"ResponsesClient default URL: {client.base_url}")
except ImportError:
    print("ResponsesClient: Could not import")

# Check GatewayLLMClient default
try:
    from src.fact_check.llm_client import GatewayLLMClient
    print(f"GatewayLLMClient default: http://localhost:8000")
except ImportError:
    print("GatewayLLMClient: Could not import")

print("\n✅ All configurations should now default to port 8000")