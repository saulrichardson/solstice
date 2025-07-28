"""Document ingestion utilities.

Main pipeline for PDF processing with layout detection, box merging, 
and reading order determination.
"""

from .layout_pipeline import LayoutDetectionPipeline  # noqa: F401
from .pipeline import ingest_pdf  # noqa: F401
from .visualize_layout import visualize_pipeline_results  # noqa: F401
from .document import Block, Document  # noqa: F401
from .storage import doc_id  # noqa: F401

__all__ = [
    # Main pipeline
    "ingest_pdf",
    
    # Core components
    "LayoutDetectionPipeline",
    "Block",
    "Document",
    
    # Utilities
    "visualize_pipeline_results",
    "doc_id",
]