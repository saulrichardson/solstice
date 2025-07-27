"""Enhanced PDF extraction pipeline with visual reordering for complex layouts.

This pipeline extends the standard extraction pipeline by adding visual analysis
for pages containing figures and tables, ensuring proper caption ordering.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from pdf2image import convert_from_path

from .pipeline_extraction import (
    ingest_pdf_for_extraction as base_ingest_pdf,
    organize_by_type,
    determine_semantic_order,
    LayoutDetectionPipeline,
    Box,
    refine_page_layout_simple,
    extract_with_specialized_extractors,
    create_semantic_document
)
from .agent.visual_reordering import (
    has_complex_elements,
    determine_semantic_order_with_vision,
    LLMClient
)

logger = logging.getLogger(__name__)


def ingest_pdf_for_extraction_with_vision(
    pdf_path: Path | str,
    detection_dpi: int = 200,
    merge_strategy: str = "weighted",
    use_vision_reordering: bool = True,
    llm_client: Optional[LLMClient] = None,
    save_debug_visualizations: bool = False
) -> List[Dict[str, Any]]:
    """Enhanced PDF ingestion with optional visual reordering for complex layouts.
    
    Args:
        pdf_path: Path to the PDF file
        detection_dpi: DPI for detection
        merge_strategy: Strategy for merging overlapping boxes
        use_vision_reordering: Whether to use vision model for complex layouts
        llm_client: LLM client for vision analysis (required if use_vision_reordering=True)
        save_debug_visualizations: Whether to save comparison images for reordered pages
        
    Returns:
        List of dictionaries, one per page, with:
        - page_num: Page number
        - organized_elements: Dict of elements by type
        - reading_order: List of element IDs in reading order
        - all_boxes: All layout boxes
        - detection_dpi: DPI used for detection
        - vision_reordered: Whether vision reordering was applied
    """
    pdf_path = Path(pdf_path)
    
    logger.info(f"Processing PDF for extraction with vision support: {pdf_path}")
    
    # Extract layout
    detector = LayoutDetectionPipeline(detection_dpi=detection_dpi)
    raw_layouts = detector.process_pdf(pdf_path)
    
    # Get page images if using vision
    page_images = None
    if use_vision_reordering:
        if llm_client is None:
            logger.warning("Vision reordering requested but no LLM client provided. Using standard ordering.")
            use_vision_reordering = False
        else:
            logger.info("Converting PDF to images for visual analysis...")
            page_images = convert_from_path(pdf_path, dpi=detection_dpi)
    
    # Process each page
    extraction_data = []
    
    for page_idx, layout in enumerate(raw_layouts):
        page_num = page_idx + 1
        logger.info(f"Processing page {page_num}/{len(raw_layouts)}")
        
        # Convert layout to boxes
        boxes = [
            Box(
                id=str(uuid.uuid4())[:8],
                bbox=(
                    block.block.x_1,
                    block.block.y_1,
                    block.block.x_2,
                    block.block.y_2,
                ),
                label=str(block.type) if block.type else "Unknown",
                score=float(block.score if hasattr(block, 'score') else 0.0),
            )
            for block in layout
        ]
        
        # Refine layout
        refined_page = refine_page_layout_simple(
            page_index=page_idx,
            raw_boxes=boxes,
            merge_strategy=merge_strategy
        )
        
        # Organize by type
        organized = organize_by_type(refined_page)
        
        # Determine semantic reading order
        all_boxes = refined_page.boxes
        
        if use_vision_reordering and has_complex_elements(all_boxes):
            # Use vision-enhanced ordering for pages with figures/tables
            page_image = page_images[page_idx] if page_images else None
            
            reading_order = determine_semantic_order_with_vision(
                boxes=all_boxes,
                page_image=page_image,
                page_width=page_image.width if page_image else 1600,
                llm_client=llm_client
            )
            
            # Check if order was changed
            original_order = determine_semantic_order(all_boxes)
            vision_reordered = (reading_order != original_order)
            
            if vision_reordered and save_debug_visualizations:
                from .agent.visual_reordering import create_debug_visualization
                debug_path = f"visual_reordering_page_{page_num:02d}.png"
                create_debug_visualization(
                    page_image, all_boxes, original_order, reading_order, debug_path
                )
                logger.info(f"Saved reordering comparison to {debug_path}")
        else:
            # Use standard column-based ordering
            reading_order = determine_semantic_order(all_boxes)
            vision_reordered = False
        
        # Log statistics
        logger.info(f"  Page {page_num}: "
                   f"{len(organized['text'])} text, "
                   f"{len(organized['figures'])} figures, "
                   f"{len(organized['tables'])} tables"
                   f"{' (vision reordered)' if vision_reordered else ''}")
        
        # Prepare extraction data
        page_data = {
            'page_num': page_num,
            'organized_elements': organized,
            'reading_order': reading_order,
            'all_boxes': refined_page.boxes,
            'detection_dpi': detection_dpi,
            'vision_reordered': vision_reordered
        }
        
        extraction_data.append(page_data)
    
    return extraction_data


def create_semantic_document_with_vision_info(
    extracted_content: Dict[str, Any],
    extraction_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Create semantic document with vision reordering metadata.
    
    Args:
        extracted_content: Output from extract_with_specialized_extractors
        extraction_data: Original extraction data with vision info
        
    Returns:
        List of content blocks in semantic reading order with vision metadata
    """
    # Use base implementation
    semantic_blocks = create_semantic_document(extracted_content)
    
    # Add vision reordering info
    vision_info = {
        data['page_num']: data.get('vision_reordered', False)
        for data in extraction_data
    }
    
    for block in semantic_blocks:
        block['vision_reordered'] = vision_info.get(block['page'], False)
    
    return semantic_blocks


# Import statement fix
import uuid