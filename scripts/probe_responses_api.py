#!/usr/bin/env python3
"""Minimal probe to inspect the raw payload returned by the OpenAI Responses API.

This is **not** part of the gateway; it is a standalone utility that helps you
verify the exact schema (especially the `output_text` field) returned by the
latest version of the Responses API.

Usage:

    # Ensure you have the latest SDK.
    pip install --upgrade "openai>=1.50.0"

    # Export your key (or set it in your shell profile).
    export OPENAI_API_KEY=sk-...

    # Run the script.
    python scripts/probe_responses_api.py

The script prints the full JSON response so you can inspect every field.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys


def _require_api_key() -> str:
    """Return `OPENAI_API_KEY` or exit with a helpful message."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: Set OPENAI_API_KEY in your environment first.", file=sys.stderr)
        sys.exit(1)
    return api_key


async def _probe() -> None:
    """Send a simple request to the Responses API and print the raw payload."""

    # Import inside the coroutine so the script still shows the missing SDK
    # message instantly if openai isn't installed.
    try:
        from openai import AsyncOpenAI  # type: ignore
    except ModuleNotFoundError:
        print(
            "ERROR: openai Python package not found. Install it with\n"
            "       pip install \"openai>=1.50.0\"",
            file=sys.stderr,
        )
        sys.exit(1)

    client = AsyncOpenAI(api_key=_require_api_key())

    import datetime as _dt

    # Probe two models: a general GPT-4 model and a reasoning (o-series) model.
    probes: list[tuple[str, str]] = [
        ("gpt-4.1", "Tell me a six-word bedtime story."),
        ("o4-mini", "Explain quantum tunnelling in one sentence."),
    ]

    for model, prompt in probes:
        request_body: dict[str, object] = {
            "model": model,
            "input": prompt,
        }

        ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        print(f"\nSending request to {model} …", file=sys.stderr)

        try:
            response = await client.responses.create(**request_body)
        except Exception as exc:  # noqa: BLE001
            print(f"Request to {model} failed: {exc}", file=sys.stderr)
            continue

        payload = response.model_dump()

        # Save to disk for later inspection.
        filename = f"responses_probe_{model.replace('/', '-')}_{ts}.json"
        with open(filename, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

        print(f"Saved raw payload to {filename}")

        # Also pretty-print to the console.
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_probe())
