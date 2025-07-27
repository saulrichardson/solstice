"""High-level orchestration that combines CV detection with LLM refinement."""

from __future__ import annotations

import os
import uuid
import base64
import io
from typing import List, Sequence

from pdf2image import convert_from_path

import layoutparser as lp

from .layout_pipeline import LayoutDetectionPipeline
from .agent.refine_layout import Box, RefinedPage, refine_page_layout

# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def ingest_pdf(pdf_path: str | os.PathLike[str], detection_dpi: int = 200) -> List[RefinedPage]:
    """Run full ingestion on *pdf_path* and return refined pages.
    
    Args:
        pdf_path: Path to PDF file
        detection_dpi: DPI for detection and processing (default: 200)
        
    Returns:
        List of refined pages with consistent DPI handling
    """

    detector = LayoutDetectionPipeline(detection_dpi=detection_dpi)
    raw_layouts: List[Sequence[lp.Layout]] = detector.process_pdf(pdf_path)

    # Rasterise pages again to obtain PIL images for vision model
    # CRITICAL: Use same DPI as detection to ensure coordinate consistency
    images = convert_from_path(str(pdf_path), fmt="png", dpi=detection_dpi)

    refined_pages: List[RefinedPage] = []
    for page_idx, (page_layout, page_img) in enumerate(zip(raw_layouts, images)):
        # Convert lp.Layout → Box dataclass for the LLM
        boxes = [
            Box(
                id=str(uuid.uuid4())[:8],
                bbox=(
                    layout.block.x_1,
                    layout.block.y_1,
                    layout.block.x_2,
                    layout.block.y_2,
                ),
                label=str(layout.type) if layout.type else "Unknown",
                score=float(layout.score or 0.0),
            )
            for layout in page_layout
        ]

        refined = refine_page_layout(page_idx, boxes, page_image=page_img)
        refined.page_index = page_idx
        refined.detection_dpi = detection_dpi
        refined_pages.append(refined)

    return refined_pages
