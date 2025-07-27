"""PDF ingestion pipeline focused on extraction with semantic ordering.

This pipeline:
1. Detects layout elements (text, figures, tables)
2. Refines and merges overlapping boxes
3. Determines semantic reading order
4. Routes each element to appropriate extractor
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import uuid
from pdf2image import convert_from_path

from .agent.refine_layout import RefinedPage, Box
from .layout_pipeline import LayoutDetectionPipeline
from .agent.refine_layout_simple import refine_page_layout_simple
from .extractors import ComponentRouter

logger = logging.getLogger(__name__)


def organize_by_type(refined_page: RefinedPage) -> Dict[str, List[Box]]:
    """Organize boxes by their type for extraction routing.
    
    Args:
        refined_page: Page with refined boxes
        
    Returns:
        Dictionary with keys 'text', 'figures', 'tables', 'lists', 'titles'
    """
    organized = {
        'text': [],
        'figures': [],
        'tables': [],
        'lists': [],
        'titles': []
    }
    
    for box in refined_page.boxes:
        if box.label == 'Text':
            organized['text'].append(box)
        elif box.label == 'Figure':
            organized['figures'].append(box)
        elif box.label == 'Table':
            organized['tables'].append(box)
        elif box.label == 'List':
            organized['lists'].append(box)
        elif box.label == 'Title':
            organized['titles'].append(box)
    
    return organized


def detect_columns(boxes: List[Box], page_width: float = 1600) -> List[List[Box]]:
    """Detect column structure in the page layout.
    
    Args:
        boxes: List of boxes to analyze
        page_width: Width of the page
        
    Returns:
        List of columns, each containing boxes in that column
    """
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
    
    # Simple approach: look for a gap in x-positions
    # More sophisticated: use clustering
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
        left_boundary = 0
        middle = (gaps[0][0] + gaps[0][1]) / 2
        right_boundary = page_width
        
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


def determine_semantic_order(boxes: List[Box], page_width: float = 1600) -> List[str]:
    """Determine reading order based on layout analysis.
    
    Handles both single and multi-column layouts:
    1. Detect column structure
    2. Read top-to-bottom within each column
    3. Move left-to-right between columns
    
    Args:
        boxes: List of boxes to order
        page_width: Width of the page for column detection
        
    Returns:
        List of box IDs in reading order
    """
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
            # This is the spanning elements group
            reading_order.extend([box.id for box in sorted_column])
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


def ingest_pdf_for_extraction(
    pdf_path: Path | str,
    detection_dpi: int = 200,
    merge_strategy: str = "weighted",
) -> List[Dict[str, Any]]:
    """Ingest PDF and prepare for element-specific extraction.
    
    Args:
        pdf_path: Path to the PDF file
        detection_dpi: DPI for detection
        merge_strategy: Strategy for merging overlapping boxes
        
    Returns:
        List of dictionaries, one per page, with:
        - page_num: Page number
        - organized_elements: Dict of elements by type
        - reading_order: List of element IDs in reading order
        - page_image: PIL Image of the page (optional)
    """
    pdf_path = Path(pdf_path)
    
    logger.info(f"Processing PDF for extraction: {pdf_path}")
    
    # Extract layout
    detector = LayoutDetectionPipeline(detection_dpi=detection_dpi)
    raw_layouts = detector.process_pdf(pdf_path)
    
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
        reading_order = determine_semantic_order(all_boxes)
        
        # Log statistics
        logger.info(f"  Page {page_num}: "
                   f"{len(organized['text'])} text, "
                   f"{len(organized['figures'])} figures, "
                   f"{len(organized['tables'])} tables")
        
        # Prepare extraction data
        page_data = {
            'page_num': page_num,
            'organized_elements': organized,
            'reading_order': reading_order,
            'all_boxes': refined_page.boxes,
            'detection_dpi': detection_dpi
        }
        
        extraction_data.append(page_data)
    
    return extraction_data


def extract_with_specialized_extractors(
    extraction_data: List[Dict[str, Any]],
    pdf_path: Path | str,
    extract_images: bool = True,
    table_method: str = "camelot"
) -> Dict[str, Any]:
    """Route elements to specialized extractors.
    
    Args:
        extraction_data: Prepared extraction data from ingest_pdf_for_extraction
        pdf_path: Path to original PDF (for text extraction)
        extract_images: Whether to extract images for figures
        table_method: Method for table extraction ("camelot", "pdfplumber", "tatr")
        
    Returns:
        Dictionary with extracted content by type
    """
    pdf_path = Path(pdf_path)
    
    # Initialize the component router
    router = ComponentRouter()
    
    # Get page images if needed for figure extraction
    page_images = None
    if extract_images:
        logger.info("Converting PDF to images for figure extraction...")
        page_images = convert_from_path(pdf_path, dpi=200)
    
    results = {
        'text_content': [],
        'tables': [],
        'figures': [],
        'metadata': {
            'total_pages': len(extraction_data),
            'pdf_path': str(pdf_path)
        }
    }
    
    for page_idx, page_data in enumerate(extraction_data):
        page_num = page_data['page_num']
        organized = page_data['organized_elements']
        reading_order = page_data['reading_order']
        detection_dpi = page_data.get('detection_dpi', 200)
        
        logger.info(f"Extracting content from page {page_num}")
        
        # Get page image for this page (if available)
        page_image = page_images[page_idx] if page_images and page_idx < len(page_images) else None
        
        # Extract text elements
        for text_box in organized['text']:
            extracted = router.extract_component(
                'text',
                pdf_path,
                page_num,
                text_box.bbox,
                detection_dpi
            )
            
            text_entry = {
                'page': page_num,
                'bbox': text_box.bbox,
                'type': 'text',
                'id': text_box.id,
                'confidence': text_box.score,
                'extracted_text': extracted.get('text', ''),
                'word_count': extracted.get('word_count', 0),
                'extraction_error': extracted.get('error')
            }
            results['text_content'].append(text_entry)
        
        # Extract titles
        for title_box in organized['titles']:
            extracted = router.extract_component(
                'title',
                pdf_path,
                page_num,
                title_box.bbox,
                detection_dpi
            )
            
            title_entry = {
                'page': page_num,
                'bbox': title_box.bbox,
                'type': 'title',
                'id': title_box.id,
                'confidence': title_box.score,
                'extracted_text': extracted.get('text', ''),
                'extraction_error': extracted.get('error')
            }
            results['text_content'].append(title_entry)
        
        # Extract lists
        for list_box in organized['lists']:
            extracted = router.extract_component(
                'list',
                pdf_path,
                page_num,
                list_box.bbox,
                detection_dpi
            )
            
            list_entry = {
                'page': page_num,
                'bbox': list_box.bbox,
                'type': 'list',
                'id': list_box.id,
                'confidence': list_box.score,
                'extracted_text': extracted.get('text', ''),
                'extraction_error': extracted.get('error')
            }
            results['text_content'].append(list_entry)
        
        # Extract tables
        for table_box in organized['tables']:
            extracted = router.extract_component(
                'table',
                pdf_path,
                page_num,
                table_box.bbox,
                detection_dpi,
                page_image=page_image,
                table_method=table_method
            )
            
            table_entry = {
                'page': page_num,
                'bbox': table_box.bbox,
                'type': 'table',
                'id': table_box.id,
                'confidence': table_box.score,
                'extracted_data': extracted.get('data', []),
                'shape': extracted.get('shape'),
                'extraction_method': extracted.get('method'),
                'raw_text': extracted.get('raw_text'),
                'extraction_error': extracted.get('error')
            }
            results['tables'].append(table_entry)
        
        # Extract figures
        for figure_box in organized['figures']:
            extracted = router.extract_component(
                'figure',
                pdf_path,
                page_num,
                figure_box.bbox,
                detection_dpi,
                page_image
            )
            
            figure_entry = {
                'page': page_num,
                'bbox': figure_box.bbox,
                'type': 'figure',
                'id': figure_box.id,
                'confidence': figure_box.score,
                'has_image': 'image' in extracted,
                'image_size': extracted.get('size'),
                'is_color': extracted.get('is_color'),
                'has_content': extracted.get('has_content'),
                'extraction_error': extracted.get('error')
            }
            
            # Store image bytes if extracted
            if 'image_bytes' in extracted:
                figure_entry['image_data'] = extracted['image_bytes']
            
            results['figures'].append(figure_entry)
    
    # Add reading order to metadata
    results['metadata']['reading_orders'] = [
        {
            'page': data['page_num'],
            'order': data['reading_order']
        }
        for data in extraction_data
    ]
    
    return results


def create_semantic_document(extracted_content: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create a semantically ordered document from extracted content.
    
    This reassembles the document in reading order, with proper
    grouping of related elements (e.g., figures with their captions).
    
    Args:
        extracted_content: Output from extract_with_specialized_extractors
        
    Returns:
        List of content blocks in semantic reading order
    """
    semantic_blocks = []
    
    # Get all elements with their reading order
    all_elements = []
    
    # Add text elements
    for text in extracted_content['text_content']:
        all_elements.append({
            'type': 'text',
            'page': text['page'],
            'id': text['id'],
            'bbox': text['bbox'],
            'content': text.get('extracted_text', ''),
            'element': text
        })
    
    # Add tables
    for table in extracted_content['tables']:
        all_elements.append({
            'type': 'table',
            'page': table['page'],
            'id': table['id'],
            'bbox': table['bbox'],
            'content': table.get('extracted_data', {}),
            'element': table
        })
    
    # Add figures
    for figure in extracted_content['figures']:
        all_elements.append({
            'type': 'figure',
            'page': figure['page'],
            'id': figure['id'],
            'bbox': figure['bbox'],
            'content': figure.get('image_data', None),
            'element': figure
        })
    
    # Group by page and sort by reading order
    pages = {}
    for elem in all_elements:
        page = elem['page']
        if page not in pages:
            pages[page] = []
        pages[page].append(elem)
    
    # Get reading orders
    reading_orders = {
        ro['page']: ro['order'] 
        for ro in extracted_content['metadata']['reading_orders']
    }
    
    # Sort elements within each page by reading order
    for page_num in sorted(pages.keys()):
        page_elements = pages[page_num]
        reading_order = reading_orders.get(page_num, [])
        
        # Create ID to position mapping
        id_to_pos = {id: i for i, id in enumerate(reading_order)}
        
        # Sort elements by their position in reading order
        sorted_elements = sorted(
            page_elements,
            key=lambda e: id_to_pos.get(e['id'], len(reading_order))
        )
        
        # Add to semantic blocks
        for elem in sorted_elements:
            semantic_blocks.append({
                'page': page_num,
                'type': elem['type'],
                'id': elem['id'],
                'bbox': elem['bbox'],
                'content': elem['content'],
                'metadata': elem['element']
            })
    
    return semantic_blocks