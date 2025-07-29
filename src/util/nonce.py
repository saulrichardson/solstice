"""Utility helper to generate unique nonces for cache-busting requests."""

from __future__ import annotations

import uuid


def new_nonce() -> str:
    """Return a short, URL-safe random nonce string (32 hex chars)."""

    # Using uuid4 gives 122 bits of randomness which is plenty for our
    # purpose while remaining deterministic in length and character set.
    return uuid.uuid4().hex

