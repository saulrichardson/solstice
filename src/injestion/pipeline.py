"""High-level orchestration for PDF layout detection and processing."""

from __future__ import annotations

import os
import uuid
import base64
import io
from typing import List, Sequence, Optional


from pdf2image import convert_from_path

from .storage.paths import pages_dir, stage_dir, save_json, load_json, final_doc_path, doc_id

import layoutparser as lp

from .processing.layout_detector import LayoutDetectionPipeline
from .models.box import Box
from .processing.overlap_resolver import no_overlap_pipeline
from .models.document import Block, Document
from .processing.text_extractor import extract_document_content
from .processing.reading_order import determine_reading_order_simple

# ---------------------------------------------------------------------------
# Column detection and reading order
# ---------------------------------------------------------------------------

def detect_columns(boxes: List[Box], page_width: float = 1600) -> List[List[Box]]:
    """Detect column structure in the page layout."""
    if not boxes:
        return []
    
    # Get horizontal positions of text boxes (exclude wide elements like titles)
    text_boxes = [b for b in boxes if b.label in ['Text', 'List']]
    if not text_boxes:
        return [boxes]
    
    # Calculate box widths to identify potential column elements
    box_widths = [(b.bbox[2] - b.bbox[0]) for b in text_boxes]
    avg_width = sum(box_widths) / len(box_widths)
    
    # Filter out wide boxes (likely titles or spanning elements)
    column_candidates = [b for b in text_boxes if (b.bbox[2] - b.bbox[0]) < page_width * 0.6]
    
    if len(column_candidates) < 4:
        # Not enough boxes to determine columns
        return [boxes]
    
    # Analyze x-positions to find column boundaries
    x_positions = sorted([b.bbox[0] for b in column_candidates])
    
    # Look for gaps in x-positions
    gaps = []
    for i in range(1, len(x_positions)):
        gap = x_positions[i] - x_positions[i-1]
        if gap > avg_width * 0.5:  # Significant gap
            gaps.append((x_positions[i-1], x_positions[i]))
    
    if not gaps:
        # No clear column separation
        return [boxes]
    
    # For now, assume 2 columns if we found a clear gap
    if len(gaps) == 1 and gaps[0][0] < page_width * 0.6:
        # Two column layout detected
        middle = (gaps[0][0] + gaps[0][1]) / 2
        
        left_column = []
        right_column = []
        spanning_elements = []
        
        for box in boxes:
            box_center = (box.bbox[0] + box.bbox[2]) / 2
            box_width = box.bbox[2] - box.bbox[0]
            
            # Check if element spans columns
            if box_width > page_width * 0.6 or (box.bbox[0] < middle - 50 and box.bbox[2] > middle + 50):
                spanning_elements.append(box)
            elif box_center < middle:
                left_column.append(box)
            else:
                right_column.append(box)
        
        return [spanning_elements, left_column, right_column]
    
    # Default: single column
    return [boxes]


def determine_reading_order(boxes: List[Box], page_width: float = 1600) -> List[str]:
    """Determine reading order based on column layout analysis."""
    if not boxes:
        return []
    
    # Detect columns
    columns = detect_columns(boxes, page_width)
    
    reading_order = []
    
    # Process each column
    for column_boxes in columns:
        if not column_boxes:
            continue
            
        # Sort boxes in column top to bottom
        sorted_column = sorted(column_boxes, key=lambda b: b.bbox[1])
        
        # For spanning elements at the top (like titles), process them first
        if len(columns) > 1 and columns[0] == column_boxes:
            # This is the spanning elements group - sort by type priority then position
            # Prioritize titles/headers at the top
            def sort_key(box):
                type_priority = 0 if box.label in ['Title', 'Header'] else 1
                return (type_priority, box.bbox[1])  # Type first, then y-position
            
            sorted_spanning = sorted(column_boxes, key=sort_key)
            reading_order.extend([box.id for box in sorted_spanning])
        else:
            # Regular column - group nearby boxes
            column_order = []
            i = 0
            while i < len(sorted_column):
                current_y = sorted_column[i].bbox[1]
                row_boxes = [sorted_column[i]]
                
                # Collect boxes at similar y-position (same row)
                j = i + 1
                while j < len(sorted_column) and abs(sorted_column[j].bbox[1] - current_y) < 20:
                    row_boxes.append(sorted_column[j])
                    j += 1
                
                # Sort row boxes left to right
                row_boxes.sort(key=lambda b: b.bbox[0])
                column_order.extend([box.id for box in row_boxes])
                
                i = j
            
            reading_order.extend(column_order)
    
    return reading_order


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


def ingest_pdf(
    pdf_path: str | os.PathLike[str], 
    detection_dpi: int = 300,
    merge_overlapping: bool = True,
    merge_threshold: float = 0.1,
    confidence_weight: float = 0.7,
    area_weight: float = 0.3,
    create_visualizations: bool = True
) -> Document:
    """Run full ingestion on *pdf_path* and return document with detected layout.
    
    Args:
        pdf_path: Path to PDF file
        detection_dpi: DPI for detection and processing (default: 300)
        merge_overlapping: Whether to merge overlapping boxes (default: True)
        merge_threshold: IoU threshold for merging same-type boxes (default: 0.1)
        confidence_weight: Weight for confidence in conflict resolution (default: 0.7)
        area_weight: Weight for box area in conflict resolution (default: 0.3)
        create_visualizations: Whether to create visualization images (default: True)
        
    Returns:
        Document object with detected and optionally merged layout elements
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

    # First pass: Process all pages to get boxes
    all_page_boxes = []
    blocks: List[Block] = []
    
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
    
    # Second pass: Determine reading order for each page
    reading_order_by_page: List[List[str]] = []
    from .processing.reading_order import Box as SimpleBox
    
    for page_idx, page_boxes in enumerate(all_page_boxes):
        page_width = images[page_idx].width if page_idx < len(images) else 1600
        
        # Convert to SimpleBox format for reading order
        simple_page_boxes = [
            SimpleBox(id=b.id, bbox=b.bbox, label=b.label, score=b.score)
            for b in page_boxes
        ]
        page_reading_order = determine_reading_order_simple(
            simple_page_boxes, page_width
        )
        
        reading_order_by_page.append(page_reading_order)

    # Skip saving raw layout - not needed for downstream

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
    
    # Skip saving column detection - intermediate data not needed
    
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

    # Save final document
    document_path = final_doc_path(pdf_path)
    document.save(document_path)
    
    # Skip saving summary - not needed for downstream processing
    
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
    
    # Extract text and figure content
    document = extract_document_content(document, pdf_path, detection_dpi)
    
    # Save the final extracted document with content
    extracted_dir = stage_dir("extracted", pdf_path)
    final_path = extracted_dir / "content.json"
    document.save(final_path)

    return document
