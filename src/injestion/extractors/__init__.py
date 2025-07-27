"""Component extractors for PDF processing."""

from .component_extractors import (
    TextExtractor,
    TableExtractor,
    FigureExtractor,
    ComponentRouter
)
from .tatr_extractor import (
    TATRStructureExtractor,
    download_tatr_weights
)

__all__ = [
    "TextExtractor",
    "TableExtractor", 
    "FigureExtractor",
    "ComponentRouter",
    "TATRStructureExtractor",
    "download_tatr_weights"
]