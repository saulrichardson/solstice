"""Scientific document processing pipeline."""

from .pipeline import ingest_pdf
from .standard_pipeline import StandardPipeline as PDFIngestionPipeline

__all__ = ["ingest_pdf", "PDFIngestionPipeline"]