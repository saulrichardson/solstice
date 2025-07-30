"""PDF document ingestion and processing package.

This package provides the core functionality for:
- Layout detection using LayoutParser
- Text extraction with PyMuPDF
- Document structuring and formatting
- Marketing-specific document processing
"""

# Import the main pipeline function from the scientific module
from .scientific import ingest_pdf, PDFIngestionPipeline

__all__ = ["ingest_pdf", "PDFIngestionPipeline"]
