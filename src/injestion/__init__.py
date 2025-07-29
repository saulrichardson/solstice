"""PDF document ingestion and processing package.

This package provides the core functionality for:
- Layout detection using LayoutParser
- Text extraction with PyMuPDF
- Document structuring and formatting
- Marketing-specific document processing
"""

# Import the main pipeline function
from .pipeline import ingest_pdf

# Re-export models from interfaces for backward compatibility
# Public re-exports
# No legacy re-exports – users should import these from ``src.interfaces``.
__all__ = ["ingest_pdf"]
