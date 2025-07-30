"""Document viewer module for creating unified views of extracted documents."""

from .aggregator import DocumentAggregator
from .html_generator import UnifiedHTMLGenerator

__all__ = ["DocumentAggregator", "UnifiedHTMLGenerator"]