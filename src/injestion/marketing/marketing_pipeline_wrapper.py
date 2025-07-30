"""Wrapper for marketing pipeline that uses separate cache directory."""

import os
from pathlib import Path
from typing import Optional

from .pipeline import MarketingPipeline
from ..shared.storage import paths
from ..shared.config import IngestionConfig


class MarketingPipelineWrapper(MarketingPipeline):
    """Marketing pipeline that uses a separate cache directory."""
    
    def __init__(self, config: Optional[IngestionConfig] = None, cache_dir: Optional[Path] = None):
        """Initialize with optional custom cache directory.
        
        Args:
            config: Optional IngestionConfig instance
            cache_dir: Optional cache directory (defaults to data/marketing_cache)
        """
        # Set custom cache directory before initializing parent
        if cache_dir is None:
            cache_dir = Path("data/marketing_cache")
        
        # Override the global cache directory for this pipeline
        self._original_cache_dir = paths._CACHE_DIR
        paths.set_cache_root(str(cache_dir))
        
        super().__init__(config)
    
    def __del__(self):
        """Restore original cache directory on cleanup."""
        if hasattr(self, '_original_cache_dir'):
            paths.set_cache_root(str(self._original_cache_dir))