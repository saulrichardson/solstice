"""Pipeline variant that uses simple geometric merging instead of LLM refinement."""

from __future__ import annotations

import os
import uuid
from typing import List, Sequence

from pdf2image import convert_from_path
import layoutparser as lp

from .layout_pipeline import LayoutDetectionPipeline
from .agent.refine_layout import Box, RefinedPage
from .agent.refine_layout_simple import refine_page_layout_simple


def ingest_pdf_simple(
    pdf_path: str | os.PathLike[str], 
    detection_dpi: int = 200,
    merge_strategy: str = "simple",
    overlap_threshold: float = 0.5,
    iou_threshold: float = 0.1,
    resolve_conflicts: bool = True,
    conflict_resolution: str = "weighted",
) -> List[RefinedPage]:
    """Run ingestion with simple geometric merging instead of LLM refinement.
    
    This is a faster, deterministic alternative to the LLM-based pipeline.
    It merges overlapping boxes of the same type using geometric rules and
    resolves cross-type conflicts using weighted scoring.
    
    Args:
        pdf_path: Path to PDF file
        detection_dpi: DPI for detection and processing (default: 200)
        merge_strategy: "simple" or "iou" merging strategy
        overlap_threshold: For "simple" strategy - fraction of overlap needed
        iou_threshold: For "iou" strategy - minimum IoU for merging
        resolve_conflicts: Whether to resolve cross-type overlaps (default: True)
        conflict_resolution: How to resolve conflicts (default: "weighted")
            - "weighted": Uses confidence (70%) + area (30%) scoring
            - "priority": Uses type hierarchy (List > Text)
            - "larger": Larger box wins
            - "confident": Higher confidence wins
        
    Returns:
        List of refined pages with merged boxes
    """
    
    detector = LayoutDetectionPipeline(detection_dpi=detection_dpi)
    raw_layouts: List[Sequence[lp.Layout]] = detector.process_pdf(pdf_path)
    
    # We don't need page images for simple merging, but we still need page count
    # so we'll just get the page count from layouts
    num_pages = len(raw_layouts)
    
    refined_pages: List[RefinedPage] = []
    
    for page_idx, page_layout in enumerate(raw_layouts):
        # Convert lp.Layout → Box dataclass
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
        
        # Apply simple geometric refinement with conflict resolution
        refined = refine_page_layout_simple(
            page_index=page_idx,
            raw_boxes=boxes,
            merge_strategy=merge_strategy,
            overlap_threshold=overlap_threshold,
            iou_threshold=iou_threshold,
            resolve_conflicts=resolve_conflicts,
            conflict_resolution=conflict_resolution,
        )
        
        # Update page metadata
        refined.page_index = page_idx
        refined.detection_dpi = detection_dpi
        
        refined_pages.append(refined)
    
    return refined_pages


def ingest_pdf_compare(
    pdf_path: str | os.PathLike[str],
    detection_dpi: int = 200,
) -> tuple[List[RefinedPage], List[RefinedPage]]:
    """Run both simple and LLM refinement for comparison.
    
    Args:
        pdf_path: Path to PDF file
        detection_dpi: DPI for detection and processing
        
    Returns:
        Tuple of (simple_refined_pages, llm_refined_pages)
    """
    
    # Run simple refinement
    simple_pages = ingest_pdf_simple(pdf_path, detection_dpi)
    
    # Run LLM refinement
    from .pipeline import ingest_pdf
    llm_pages = ingest_pdf(pdf_path, detection_dpi)
    
    return simple_pages, llm_pages