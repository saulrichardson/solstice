import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

# Local
from .config import settings

logger = logging.getLogger("gateway.cache")


class Cache:
    """Filesystem-based cache for LLM responses (single-node friendly)."""

    def __init__(self):
        # The cache is write-only; files are persisted for audit/debugging
        # but never read by the application during execution.
        self.root: Path = Path(settings.filesystem_cache_dir).expanduser()
        self.cache_enabled = True  # Track if cache is operational

    async def connect(self):
        """Create cache directory if caching is enabled."""
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            logger.info("Gateway snapshots will be written to %s", self.root)
        except OSError as exc:
            self.cache_enabled = False
            logger.error("Failed to create gateway snapshot dir %s (%s) – snapshots disabled", self.root, exc)

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
    # Public API
    # ------------------------------------------------------------------
    
    def is_operational(self) -> bool:
        """Check if cache is operational."""
        return self.cache_enabled

    async def set_response(self, cache_data: dict, response: dict):
        if not self.cache_enabled:
            return  # Skip caching if disabled due to initialization failure
            
        key_hash = self._generate_key(cache_data)
        path = self._path_for_key(key_hash)

        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(response, f)
            os.utime(path, None)  # update mtime
            logger.info("Cached response under key %s", key_hash[:16])
        except OSError as exc:
            logger.error("Cache write error for %s: %s", path, exc)
            # Don't disable cache for individual write failures, as they might be transient

    # ------------------------------------------------------------------
    # Maintenance helpers
    # ------------------------------------------------------------------

    async def clear(self) -> None:
        """Remove all cache entries on the local filesystem.

        This is primarily intended for test suites and administrative tools
        that need to ensure a clean slate between runs.  The method is a no-op
        when caching is disabled so that calling code does not have to branch
        on the `enabled` flag.
        """

        # Ensure the root directory exists.  We purposefully *do not* create
        # it when missing – if the cache has never been initialised there's
        # nothing to clear.
        if not self.root.exists():
            return

        # Iterate over all files with the expected `.json` suffix and attempt
        # to delete them.  We isolate each deletion so that a single failure
        # (e.g. a permissions error on one file) does not abort the entire
        # cleanup.  Any exception is logged on DEBUG level only – callers that
        # require stronger guarantees should remove the directory tree
        # themselves.
        for entry in list(self.root.glob("*.json")):
            try:
                entry.unlink(missing_ok=True)
            except OSError as exc:
                logger.debug("Failed to delete cache file %s: %s", entry, exc)

        # Optionally remove empty cache directory to keep workspace tidy.
        try:
            # Only attempt removal if the directory is now empty to avoid
            # inadvertently deleting user files placed in the cache dir.
            self.root.rmdir()
        except OSError:
            # Directory not empty or cannot be removed – that's fine.
            pass



# Global cache instance
cache = Cache()
