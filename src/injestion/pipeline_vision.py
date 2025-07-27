"""Enhanced PDF ingestion pipeline with vision-based caption association.

This pipeline extends the simple pipeline by adding vision-based caption
association to group figures and tables with their captions.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
from pdf2image import convert_from_path

from .agent.refine_layout import RefinedPage, Box
from .layout_pipeline import LayoutDetectionPipeline
from .agent.refine_layout_simple import refine_page_layout_simple
from .agent.merge_boxes_weighted import smart_merge_and_resolve
from .agent.caption_association_vision import create_extraction_ready_groups_vision

logger = logging.getLogger(__name__)


def ingest_pdf_vision(
    pdf_path: Path | str,
    detection_dpi: int = 200,
    merge_strategy: str = "weighted",
    use_vision_captions: bool = True,
    debug: bool = False
) -> List[RefinedPage]:
    """Ingest a PDF with vision-based caption association.
    
    Args:
        pdf_path: Path to the PDF file
        detection_dpi: DPI for detection and processing
        merge_strategy: "simple", "iou", or "weighted" merging
        use_vision_captions: Whether to use vision-based caption association
        debug: Whether to save debug outputs
        
    Returns:
        List of RefinedPage objects with extraction groups
    """
    pdf_path = Path(pdf_path)
    
    logger.info(f"Processing PDF with vision pipeline: {pdf_path}")
    
    # Extract layout using detector
    detector = LayoutDetectionPipeline(detection_dpi=detection_dpi)
    raw_layouts = detector.process_pdf(pdf_path)
    
    # Get page images if using vision
    page_images = None
    if use_vision_captions:
        logger.info("Converting PDF to images for vision analysis...")
        page_images = convert_from_path(pdf_path, dpi=detection_dpi)
    
    # Process each page
    refined_pages = []
    
    for page_idx, layout in enumerate(raw_layouts):
        logger.info(f"Processing page {page_idx + 1}/{len(raw_layouts)}")
        
        # Refine layout using simple refinement
        refined_page = refine_page_layout_simple(
            layout=layout,
            page_idx=page_idx,
            merge_strategy=merge_strategy,
            detection_dpi=detection_dpi
        )
        
        # Apply vision-based caption association if enabled
        if use_vision_captions and page_images:
            logger.debug(f"Associating captions with vision on page {page_idx + 1}")
            page_image = page_images[page_idx]
            
            extraction_groups = create_extraction_ready_groups_vision(
                page_image=page_image,
                boxes=refined_page.boxes,
                reading_order=refined_page.reading_order,
                debug=debug
            )
            
            # Add extraction groups to the refined page
            # Since RefinedPage is a Pydantic model, we need to extend it
            # For now, we'll store it as a property
            refined_page.extraction_groups = extraction_groups
            
            # Log results
            n_figs = len(extraction_groups.get("figure_groups", []))
            n_figs_with_captions = sum(
                1 for g in extraction_groups.get("figure_groups", []) 
                if g.caption
            )
            n_tables = len(extraction_groups.get("table_groups", []))
            n_tables_with_captions = sum(
                1 for g in extraction_groups.get("table_groups", []) 
                if g.caption
            )
            
            if n_figs > 0 or n_tables > 0:
                logger.info(
                    f"Page {page_idx + 1}: "
                    f"{n_figs_with_captions}/{n_figs} figures and "
                    f"{n_tables_with_captions}/{n_tables} tables with captions"
                )
        
        refined_pages.append(refined_page)
    
    return refined_pages


def extract_content_with_groups(pages: List[RefinedPage]) -> Dict[str, Any]:
    """Extract content organized by semantic groups.
    
    Args:
        pages: List of RefinedPage objects with optional extraction groups
        
    Returns:
        Dictionary with extracted content organized by type
    """
    extracted = {
        "figures": [],
        "tables": [],
        "text": [],
        "metadata": {
            "total_pages": len(pages),
            "total_figures": 0,
            "total_tables": 0,
            "figures_with_captions": 0,
            "tables_with_captions": 0
        }
    }
    
    for page in pages:
        page_num = page.page_index + 1
        
        if not hasattr(page, 'extraction_groups') or not page.extraction_groups:
            # Fallback to basic extraction
            for box in page.boxes:
                if box.label == "Figure":
                    extracted["figures"].append({
                        "page": page_num,
                        "bbox": box.bbox,
                        "confidence": box.score
                    })
                    extracted["metadata"]["total_figures"] += 1
                elif box.label == "Table":
                    extracted["tables"].append({
                        "page": page_num,
                        "bbox": box.bbox,
                        "confidence": box.score
                    })
                    extracted["metadata"]["total_tables"] += 1
                elif box.label == "Text":
                    extracted["text"].append({
                        "page": page_num,
                        "bbox": box.bbox,
                        "confidence": box.score
                    })
        else:
            # Use semantic groups
            groups = page.extraction_groups
            
            # Process figures
            for group in groups.get("figure_groups", []):
                figure_data = {
                    "page": page_num,
                    "bbox": group.primary_element.bbox,
                    "confidence": group.primary_element.score,
                    "has_caption": group.caption is not None,
                    "caption_bbox": group.caption.bbox if group.caption else None,
                    "group_confidence": group.confidence
                }
                extracted["figures"].append(figure_data)
                extracted["metadata"]["total_figures"] += 1
                if group.caption:
                    extracted["metadata"]["figures_with_captions"] += 1
            
            # Process tables
            for group in groups.get("table_groups", []):
                table_data = {
                    "page": page_num,
                    "bbox": group.primary_element.bbox,
                    "confidence": group.primary_element.score,
                    "has_caption": group.caption is not None,
                    "caption_bbox": group.caption.bbox if group.caption else None,
                    "group_confidence": group.confidence
                }
                extracted["tables"].append(table_data)
                extracted["metadata"]["total_tables"] += 1
                if group.caption:
                    extracted["metadata"]["tables_with_captions"] += 1
            
            # Process text
            for group in groups.get("text_groups", []):
                text_data = {
                    "page": page_num,
                    "bbox": group.primary_element.bbox,
                    "confidence": group.primary_element.score
                }
                extracted["text"].append(text_data)
    
    return extracted