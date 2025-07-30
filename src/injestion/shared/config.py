"""Centralized configuration for the ingestion pipeline.

This module provides a single source of truth for all ingestion settings,
eliminating scattered hardcoded values across the pipeline.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class IngestionConfig:
    """Immutable configuration for PDF ingestion pipeline."""
    
    # Detection Settings
    detection_dpi: int = 400  # DPI for PDF rasterization
    score_threshold: float = 0.2  # Detection confidence threshold
    nms_threshold: float = 0.5  # Non-maximum suppression threshold
    
    # Box Processing
    expand_boxes: bool = True  # Whether to expand boxes to prevent text cutoff
    box_padding: float = 5.0  # Pixels to expand in each direction (balanced approach)
    
    # Overlap Resolution
    merge_overlapping: bool = True  # Whether to merge overlapping boxes
    merge_threshold: float = 0.1  # IoU threshold for merging same-type boxes (reduced from 0.3)
    confidence_weight: float = 0.7  # Weight for confidence in conflict resolution
    area_weight: float = 0.3  # Weight for box area in conflict resolution
    minor_overlap_threshold: float = 0.10  # Overlaps below this ratio are considered minor and kept
    
    # Visualization
    create_visualizations: bool = True  # Whether to create layout visualizations
    
    # Text Processing
    apply_text_processing: bool = True  # Whether to apply text cleaning/correction
    
    # Debug and Tracking
    save_intermediate_states: bool = False  # Save raw and merged layouts for debugging
    
    # Marketing Document Presets (can be activated via CLI)
    marketing_defaults: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize marketing defaults."""
        if self.marketing_defaults is None:
            object.__setattr__(self, 'marketing_defaults', {
                'score_threshold': 0.15,
                'nms_threshold': 0.4,
                'merge_threshold': 0.2,
            })


# Global default configuration
DEFAULT_CONFIG = IngestionConfig()

# Preset configurations for different document types
PRESETS = {
    'clinical': IngestionConfig(),  # Default is optimized for clinical
    
    'marketing': IngestionConfig(
        score_threshold=0.15,  # Lower to catch subtle design elements
        nms_threshold=0.4,  # Less aggressive NMS for marketing layouts
        merge_threshold=0.2,  # More aggressive merging
    ),
    
    'conservative': IngestionConfig(
        merge_threshold=0.5,  # Less aggressive merging
        box_padding=5.0,  # Minimal padding
        expand_boxes=False,  # Don't expand boxes
    ),
    
    'aggressive': IngestionConfig(
        merge_threshold=0.05,  # Very aggressive merging (was 0.1)
        box_padding=10.0,  # Moderate padding
        score_threshold=0.1,  # Catch everything
    ),
    
    'single-column': IngestionConfig(
        merge_threshold=0.1,  # Lower threshold for merging
        box_padding=5.0,  # Minimal padding
        score_threshold=0.2,  # Standard detection
        # Note: The 80% same-type merge threshold is hardcoded in overlap_resolver.py
    ),
}


def get_config(preset: str = 'clinical') -> IngestionConfig:
    """Get configuration for a specific preset.
    
    Args:
        preset: Name of the preset ('clinical', 'marketing', 'conservative', 'aggressive')
        
    Returns:
        IngestionConfig instance
    """
    return PRESETS.get(preset, DEFAULT_CONFIG)