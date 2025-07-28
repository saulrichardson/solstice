"""High-level orchestration for PDF layout detection and processing."""

from __future__ import annotations

import os
import uuid
import base64
import io
from typing import List, Sequence, Optional, Tuple


from pdf2image import convert_from_path

from .storage.paths import pages_dir, stage_dir, save_json, load_json, doc_id

import layoutparser as lp

from .processing.layout_detector import LayoutDetectionPipeline
from .models.box import Box
from .processing.overlap_resolver import no_overlap_pipeline
from .models.document import Block, Document
from .processing.text_extractor import extract_document_content
from .processing.reading_order import determine_reading_order_simple
from .visualization.layout_visualizer import visualize_page_layout

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _save_page_images(pdf_path: str | os.PathLike[str], detection_dpi: int) -> List:
    """Rasterize PDF pages to PNG images and save them.
    
    Args:
        pdf_path: Path to PDF file
        detection_dpi: DPI for image conversion
        
    Returns:
        List of PIL images
    """
    page_dir = pages_dir(pdf_path)
    images = list(convert_from_path(str(pdf_path), fmt="png", dpi=detection_dpi))
    for idx, img in enumerate(images):
        img.save(page_dir / f"page-{idx:03}.png")
    return images


def _process_page_layouts(
    raw_layouts: List[Sequence[lp.Layout]], 
    merge_overlapping: bool,
    merge_threshold: float,
    confidence_weight: float,
    area_weight: float,
    detection_dpi: int
) -> Tuple[List[List[Box]], List[Block]]:
    """Process raw layouts into boxes and blocks.
    
    Args:
        raw_layouts: Raw layout detections from LayoutParser
        merge_overlapping: Whether to merge overlapping boxes
        merge_threshold: IoU threshold for merging same-type boxes
        confidence_weight: Weight for confidence in conflict resolution
        area_weight: Weight for area in conflict resolution
        detection_dpi: DPI used for detection
        
    Returns:
        Tuple of (all_page_boxes, blocks)
    """
    all_page_boxes = []
    blocks = []
    
    for page_idx, page_layout in enumerate(raw_layouts):
        # Convert layout elements to Box objects for merging
        page_boxes = [
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
        
        # Apply merging if requested
        if merge_overlapping and page_boxes:
            # Always use no-overlap pipeline to guarantee clean output
            page_boxes = no_overlap_pipeline(
                boxes=page_boxes,
                merge_same_type_first=True,
                merge_threshold=merge_threshold,
                confidence_weight=confidence_weight,
                area_weight=area_weight
            )
        
        # Store processed boxes for this page
        all_page_boxes.append(page_boxes)
        
        # Convert Box objects to Block objects
        for box in page_boxes:
            block = Block(
                id=box.id,
                page_index=page_idx,
                role=box.label,
                bbox=box.bbox,
                metadata={
                    "score": box.score,
                    "detection_dpi": detection_dpi
                }
            )
            blocks.append(block)
    
    return all_page_boxes, blocks


def _create_raw_layout_visualizations(
    pdf_path: str | os.PathLike[str],
    raw_layouts: List[Sequence[lp.Layout]],
    images: List
) -> None:
    """Create visualizations for raw layout detections.
    
    Args:
        pdf_path: Path to PDF file
        raw_layouts: Raw layout detections from LayoutParser
        images: Page images
    """
    raw_dir = stage_dir("raw_layouts", pdf_path)
    viz_dir = raw_dir / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    
    for page_idx, (page_layout, page_image) in enumerate(zip(raw_layouts, images)):
        # Convert raw layouts to Box objects for visualization
        raw_boxes = []
        for layout in page_layout:
            box = Box(
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
            raw_boxes.append(box)
        
        # Convert to Block objects for visualization
        blocks = [
            Block(
                id=box.id,
                page_index=page_idx,
                role=box.label,
                bbox=box.bbox,
                metadata={"score": box.score}
            )
            for box in raw_boxes
        ]
        
        # Create visualization
        save_path = viz_dir / f"page_{page_idx + 1:03d}_raw_layout.png"
        visualize_page_layout(
            page_image,
            blocks,
            reading_order=None,  # No reading order for raw layouts
            title=f"Page {page_idx + 1} - Raw Layout Detection",
            save_path=save_path,
            show_labels=True,
            show_reading_order=False
        )


def _save_pipeline_outputs(
    pdf_path: str | os.PathLike[str],
    blocks: List[Block],
    reading_order_by_page: List[List[str]],
    raw_layouts: List[Sequence[lp.Layout]]
) -> None:
    """Save intermediate pipeline outputs.
    
    Args:
        pdf_path: Path to PDF file
        blocks: Processed blocks
        reading_order_by_page: Reading order for each page
        raw_layouts: Raw layout detections
    """
    # Save raw layout results (before any merging/overlap resolution)
    raw_dir = stage_dir("raw_layouts", pdf_path)
    raw_data = []
    for page_idx, page_layout in enumerate(raw_layouts):
        page_raw_boxes = []
        for layout in page_layout:
            page_raw_boxes.append({
                "id": str(uuid.uuid4())[:8],
                "bbox": [
                    layout.block.x_1,
                    layout.block.y_1,
                    layout.block.x_2,
                    layout.block.y_2
                ],
                "label": str(layout.type) if layout.type else "Unknown",
                "score": float(layout.score or 0.0)
            })
        raw_data.append(page_raw_boxes)
    save_json(raw_data, raw_dir / "raw_layout_boxes.json")
    
    # Save merged layout results
    merged_dir = stage_dir("merged", pdf_path)
    merged_data = []
    for page_idx in range(len(raw_layouts)):
        page_blocks = [b for b in blocks if b.page_index == page_idx]
        merged_data.append([
            {
                "id": b.id,
                "bbox": b.bbox,
                "label": b.role,
                "score": b.metadata.get("score", 0)
            }
            for b in page_blocks
        ])
    save_json(merged_data, merged_dir / "merged_boxes.json")
    
    # Save reading order
    order_dir = stage_dir("reading_order", pdf_path)
    save_json({
        "pages": [
            {
                "page": idx,
                "reading_order": order,
                "num_elements": len(order)
            }
            for idx, order in enumerate(reading_order_by_page)
        ]
    }, order_dir / "reading_order.json")


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def ingest_pdf(
    pdf_path: str | os.PathLike[str], 
    detection_dpi: int = 400,
    merge_overlapping: bool = True,
    merge_threshold: float = 0.3,
    confidence_weight: float = 0.7,
    area_weight: float = 0.3,
    create_visualizations: bool = True
) -> Document:
    """Run full ingestion on *pdf_path* and return document with detected layout.
    
    Args:
        pdf_path: Path to PDF file
        detection_dpi: DPI for detection and processing (default: 400)
        merge_overlapping: Whether to merge overlapping boxes (default: True)
        merge_threshold: IoU threshold for merging same-type boxes (default: 0.3)
        confidence_weight: Weight for confidence in conflict resolution (default: 0.7)
        area_weight: Weight for box area in conflict resolution (default: 0.3)
        create_visualizations: Whether to create visualization images (default: True)
        
    Returns:
        Document object with detected and optionally merged layout elements
    """

    # Initialize detector
    detector = LayoutDetectionPipeline(detection_dpi=detection_dpi)

    # Save page images for downstream processing
    images = _save_page_images(pdf_path, detection_dpi)

    # Run detection on the PDF
    raw_layouts: List[Sequence[lp.Layout]] = detector.process_pdf(pdf_path)

    # Create visualizations of raw layouts if requested
    if create_visualizations:
        _create_raw_layout_visualizations(pdf_path, raw_layouts, images)

    # Process all pages to get boxes and blocks
    all_page_boxes, blocks = _process_page_layouts(
        raw_layouts,
        merge_overlapping,
        merge_threshold,
        confidence_weight,
        area_weight,
        detection_dpi
    )
    
    # Second pass: Determine reading order for each page
    reading_order_by_page: List[List[str]] = []
    
    for page_idx, page_boxes in enumerate(all_page_boxes):
        page_width = images[page_idx].width if page_idx < len(images) else 1600
        
        page_reading_order = determine_reading_order_simple(
            page_boxes, page_width
        )
        
        reading_order_by_page.append(page_reading_order)

    # Save intermediate outputs
    _save_pipeline_outputs(pdf_path, blocks, reading_order_by_page, raw_layouts)
    
    # Create Document object with detected blocks and reading order
    document = Document(
        source_pdf=str(pdf_path), 
        blocks=blocks, 
        metadata={
            "detection_dpi": detection_dpi,
            "total_pages": len(raw_layouts),
            "merge_settings": {
                "merge_overlapping": merge_overlapping,
                "merge_threshold": merge_threshold,
                "confidence_weight": confidence_weight,
                "area_weight": area_weight
            }
        },
        reading_order=reading_order_by_page
    )
    
    # Extract text and figure content
    document = extract_document_content(document, pdf_path, detection_dpi)
    
    # Save the final extracted document with content
    extracted_dir = stage_dir("extracted", pdf_path)
    final_path = extracted_dir / "content.json"
    document.save(final_path)
    
    # Generate human-readable versions
    from .processing.document_formatter import (
        generate_readable_document,
        generate_text_only_document,
        generate_html_document
    )
    
    # Generate markdown version with embedded images
    markdown_path = extracted_dir / "document.md"
    generate_readable_document(document, markdown_path, include_images=True)
    
    # Generate plain text version
    text_path = extracted_dir / "document.txt"
    generate_text_only_document(document, text_path, include_placeholders=True)
    
    # Generate HTML version
    html_path = extracted_dir / "document.html"
    generate_html_document(document, html_path, include_images=True)
    
    # Create visualizations if requested
    if create_visualizations:
        from .visualization.layout_visualizer import visualize_document
        
        viz_paths = visualize_document(
            document,
            pdf_path,
            pages_to_show=None,  # Always visualize ALL pages
            show_labels=True,
            show_reading_order=True
        )
        # Visualizations saved directly by visualize_document

    return document
