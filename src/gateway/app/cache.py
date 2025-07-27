import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

# Local
from .config import settings

logger = logging.getLogger("gateway.cache")


class Cache:
    """Filesystem-based cache for LLM responses (single-node friendly)."""

    def __init__(self):
        self.enabled: bool = bool(settings.solstice_cache_enabled)
        self.ttl: int = settings.solstice_cache_ttl
        self.root: Path = Path(settings.filesystem_cache_dir).expanduser()

    async def connect(self):
        """Create cache directory if caching is enabled."""
        if not self.enabled:
            return
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            logger.info("Filesystem cache initialised at %s", self.root)
        except OSError as exc:
            logger.warning("Cache disabled; failed to create dir %s (%s)", self.root, exc)
            self.enabled = False

    async def disconnect(self):
        # Nothing to do for filesystem cache
        return

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_key(self, cache_data: dict) -> str:
        """Generate deterministic filename from request parameters."""
        key_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _path_for_key(self, key_hash: str) -> Path:
        return self.root / f"{key_hash}.json"

    # ------------------------------------------------------------------
    # Public API (async for parity with previous Redis version)
    # ------------------------------------------------------------------

    async def get_response(self, cache_data: dict) -> Optional[dict]:
        if not self.enabled:
            return None

        key_hash = self._generate_key(cache_data)
        path = self._path_for_key(key_hash)

        if not path.exists():
            return None

        # Check TTL expiry based on file modification time
        if time.time() - path.stat().st_mtime > self.ttl:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Cache hit for key %s", key_hash[:16])
            return data
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Cache read error for %s: %s", path, exc)
            return None

    async def set_response(self, cache_data: dict, response: dict):
        if not self.enabled:
            return

        key_hash = self._generate_key(cache_data)
        path = self._path_for_key(key_hash)

        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(response, f)
            os.utime(path, None)  # update mtime
            logger.info("Cached response under key %s", key_hash[:16])
        except OSError as exc:
            logger.warning("Cache write error for %s: %s", path, exc)


# Global cache instance
cache = Cache()
