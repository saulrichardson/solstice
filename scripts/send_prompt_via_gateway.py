#!/usr/bin/env python3
"""send_prompt_via_gateway.py

Utility script that submits a prompt to the Solstice LLM Gateway and prints
the model's response along with basic token-usage statistics.

The script is intentionally dependency-light - it only requires *httpx* (which
is already part of the project's dependency tree).

Usage
-----
    python scripts/send_prompt_via_gateway.py "Your prompt here"

If no prompt is supplied via the command line the PROMPT environment variable
is used instead, or a default fallback prompt when neither is given.

Environment variables
---------------------
SOLSTICE_GATEWAY_URL   Root URL of the gateway (default http://localhost:4000)
MODEL                  Model to use (default gpt-4o-mini)
TEMPERATURE            Sampling temperature (default 0.7)
PROMPT                 Prompt when no CLI arg is provided.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import httpx

# Load .env if python-dotenv is available; otherwise silence absence.
try:
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def load_dotenv() -> None:  # type: ignore
        """Fallback load_dotenv when python-dotenv is not installed."""
        return None


# Make .env variables available so OPENAI_API_KEY etc. are picked up by the
# gateway, assuming it is running in the same environment.
load_dotenv()


async def _run() -> None:
    prompt = (
        " ".join(sys.argv[1:]).strip()
        or os.environ.get("PROMPT", "🌞 Hello Solstice! Tell me a fun fact.")
    )

    base_url = os.environ.get("SOLSTICE_GATEWAY_URL", "http://localhost:8000").rstrip("/")
    endpoint = f"{base_url}/v1/responses"

    model = os.environ.get("MODEL", "gpt-4o-mini")
    temperature = float(os.environ.get("TEMPERATURE", "0.7"))

    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "temperature": temperature,
    }

    print(f"🚀  Sending request to {endpoint}\n    model       = {model}\n    temperature = {temperature}\n    prompt      = {prompt!r}\n")

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"❌  Request failed: {exc}")
            if hasattr(exc, "response") and exc.response is not None:
                print(exc.response.text)
            sys.exit(1)

    data: dict[str, Any] = response.json()

    print("✅  Response received:\n" + "-" * 60)

    # Extract the first text chunk if available
    output = ""
    if isinstance(data.get("output"), list) and data["output"]:
        output = data["output"][0].get("text", "")

    print(output or "<no text in response>")

    # Token usage stats (may not always be present)
    usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
    print("-" * 60)
    print("📊  Usage:")
    print(f"    input_tokens  : {usage.get('prompt_tokens', data.get('input_tokens', 'N/A'))}")
    print(f"    output_tokens : {usage.get('completion_tokens', data.get('output_tokens', 'N/A'))}")
    print(f"    total_tokens  : {usage.get('total_tokens', 'N/A')}")

    print(f"\n🆔  Response ID: {data.get('id', 'N/A')}")


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("Interrupted by user")


if __name__ == "__main__":
    main()
