"""Document ingestion utilities.

At the moment this subpackage only exposes a wrapper around *layoutparser* that
detects high-level layout elements (text boxes, tables, figures …) on each page
of a PDF.  Later modules (e.g. an agentic loop that refines those boxes with
an LLM) can live here as well, reusing the public API surface.
"""

from .layout_pipeline import LayoutDetectionPipeline  # noqa: F401

__all__ = [
    "LayoutDetectionPipeline",
]

