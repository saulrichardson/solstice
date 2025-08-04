"""Scientific document processing pipeline."""

from .pipeline import ingest_pdf
# Single operating model - use StandardPipeline directly
from .standard_pipeline import StandardPipeline

__all__ = ["ingest_pdf", "StandardPipeline"]