"""Component extractors for PDF processing."""

from .component_extractors import (
    TextExtractor,
    TableExtractor,
    FigureExtractor,
    ComponentRouter
)
from .tatr_extractor import ProperTATRExtractor

__all__ = [
    "TextExtractor",
    "TableExtractor", 
    "FigureExtractor",
    "ComponentRouter",
    "ProperTATRExtractor"
]