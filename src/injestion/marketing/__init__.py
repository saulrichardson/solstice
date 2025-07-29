"""Marketing document processing module.

This module provides specialized layout detection and processing for marketing materials
using PrimaLayout and optional vision LLM adjustments.
"""

from .detector import MarketingLayoutDetector
from .pipeline import MarketingPipeline

__all__ = ["MarketingLayoutDetector", "MarketingPipeline"]