"""High-level orchestration for PDF layout detection and processing."""

from __future__ import annotations

import os
from src.interfaces import Document
# No config import needed - pipeline uses its own defaults

def ingest_pdf(pdf_path: str | os.PathLike[str]) -> Document:
    """Process a PDF file with optimized settings for clinical documents.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Document object with detected layout elements, extracted text, and visualizations
    """
    from .standard_pipeline import StandardPipeline
    pipeline = StandardPipeline()  # Uses optimized defaults
    return pipeline.process_pdf(pdf_path)


# Simple entry point - no backward compatibility needed
