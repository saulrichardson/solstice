"""High-level orchestration for PDF layout detection and processing."""

from __future__ import annotations

import os
from src.interfaces import Document
from ..shared.config import get_config

def ingest_pdf(pdf_path: str | os.PathLike[str]) -> Document:
    """Process a PDF file with optimized settings for clinical documents.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Document object with detected layout elements, extracted text, and visualizations
    """
    from .standard_pipeline import StandardPipeline
    config = get_config('clinical')
    pipeline = StandardPipeline(config=config)
    return pipeline.process_pdf(pdf_path)


# Alias for backward compatibility
PDFIngestionPipeline = None  # Will be imported from standard_pipeline in __init__.py
