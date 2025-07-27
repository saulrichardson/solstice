#!/usr/bin/env python3
"""check_gateway_health.py

Quick health-check script for the Solstice LLM Gateway.

The script makes a GET request to the gateway's /health endpoint and prints
the returned status in a human-friendly way.  It exits with a non-zero status
code if the request fails or the gateway reports an unhealthy status so that
it can be used in CI/CD or monitoring probes.

Environment variables
---------------------
SOLSTICE_GATEWAY_HEALTH_URL  Full URL for the health endpoint
                            (default: http://localhost:8000/health)
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx


async def _check() -> None:
    """Perform the health check and print the result."""

    url = os.environ.get("SOLSTICE_GATEWAY_HEALTH_URL", "http://localhost:8000/health")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5)
            response.raise_for_status()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌  Gateway health request failed: {exc}")
            sys.exit(1)

    try:
        payload: dict[str, object] = response.json()
    except ValueError as exc:  # invalid JSON
        print(f"❌  Invalid JSON returned from health endpoint: {exc}")
        sys.exit(1)

    status = payload.get("status", "unknown")
    print("✅  Gateway responded to /health")
    print(f"   • status          : {status}")
    print(f"   • providers       : {payload.get('providers')}")
    print(f"   • cache_enabled   : {payload.get('cache_enabled')}")
    print(f"   • api_version     : {payload.get('api_version')}")

    if status != "healthy":
        sys.exit(2)


def main() -> None:
    """Entry point wrapper so the script can be used with "python -m" too."""

    try:
        asyncio.run(_check())
    except KeyboardInterrupt:
        print("Interrupted by user")


if __name__ == "__main__":
    main()
