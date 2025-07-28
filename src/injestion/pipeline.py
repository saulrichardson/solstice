"""High-level orchestration that combines CV detection with LLM refinement."""

from __future__ import annotations

import os
import uuid
import base64
import io
from typing import List, Sequence


from pdf2image import convert_from_path

from .storage import pages_dir, stage_dir, save_json, final_doc_path

import layoutparser as lp

from .layout_pipeline import LayoutDetectionPipeline
from .agent.refine_layout import Box, RefinedPage, refine_page_layout
from .document import Block, Document

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

    # Rasterise pages to PNG – used both for detection (inside detector) and
    # for vision model crops.  We save them so that downstream stages (e.g.
    # OCR) do not have to run pdf2image again.
    page_dir = pages_dir(pdf_path)
    images = list(convert_from_path(str(pdf_path), fmt="png", dpi=detection_dpi))
    for idx, img in enumerate(images):
        img.save(page_dir / f"page-{idx:03}.png")

    # Run detection on the same images (avoids double rasterisation)
    raw_layouts: List[Sequence[lp.Layout]] = detector.process_pdf(pdf_path)

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

    # Save raw layout detection output for debugging / future stages
    layout_dir = stage_dir("layout", pdf_path)
    save_json(
        [
            [l.to_dict() for l in page_layout]
            for page_layout in raw_layouts
        ],
        layout_dir / "layout.json",
    )

    # Assemble final Document object with placeholders for text/tables/figures
    blocks: List[Block] = []
    for refined in refined_pages:
        for b in refined.boxes:
            blocks.append(
                Block(
                    id=b.id,
                    page_index=refined.page_index,
                    role=b.label,
                    bbox=b.bbox,
                )
            )

    document = Document(source_pdf=str(pdf_path), blocks=blocks, metadata={})

    # Persist artefacts
    # 1. raster pages already saved earlier
    stage_dir("refine", pdf_path).mkdir(parents=True, exist_ok=True)
    save_json([p.model_dump() for p in refined_pages], stage_dir("refine", pdf_path) / "refined.json")

    document_path = final_doc_path(pdf_path)
    document.save(document_path)

    return refined_pages
