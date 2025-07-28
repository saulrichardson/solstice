"""Native PDF text extraction using bounding boxes from layout detection."""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image
import numpy as np

from ..models.document import Document, Block
from ..storage.paths import stage_dir

logger = logging.getLogger(__name__)


def extract_text_from_bbox(
    pdf_path: Path,
    page_num: int,
    bbox: Tuple[float, float, float, float],
    page_height: float
) -> str:
    """Extract text from PDF at specific bbox coordinates.
    
    Args:
        pdf_path: Path to PDF file
        page_num: 0-based page number
        bbox: Bounding box (x1, y1, x2, y2) in image coordinates
        page_height: Height of the page in image coordinates for conversion
        
    Returns:
        Extracted text string
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Convert image coordinates to PDF coordinates
    # Image coordinates: origin at top-left, y increases downward
    # PDF coordinates: origin at bottom-left, y increases upward
    pdf_height = page.rect.height
    scale_factor = pdf_height / page_height
    
    # Convert and scale coordinates
    x1 = bbox[0] * scale_factor
    y1 = bbox[1] * scale_factor
    x2 = bbox[2] * scale_factor
    y2 = bbox[3] * scale_factor
    
    # Create rect in PDF coordinate system
    rect = fitz.Rect(x1, y1, x2, y2)
    
    # Extract text from the rectangle
    text = page.get_text("text", clip=rect)
    
    doc.close()
    
    # Clean up extracted text
    text = text.strip()
    return text


def extract_figure_image(
    pdf_path: Path,
    page_num: int,
    bbox: Tuple[float, float, float, float],
    dpi: int = 300
) -> Image.Image:
    """Extract figure/table as image from PDF.
    
    Args:
        pdf_path: Path to PDF file
        page_num: 0-based page number
        bbox: Bounding box (x1, y1, x2, y2) in image coordinates
        dpi: DPI for rendering
        
    Returns:
        PIL Image of the cropped region
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Render page at specified DPI
    mat = fitz.Matrix(dpi/72.0, dpi/72.0)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    doc.close()
    
    # Open as PIL Image and crop
    from io import BytesIO
    full_page = Image.open(BytesIO(img_data))
    
    # Crop to bbox (already in image coordinates)
    cropped = full_page.crop((int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])))
    
    return cropped


def extract_document_content(
    document: Document,
    pdf_path: Path,
    dpi: int = 300
) -> Document:
    """Extract text and figure content for all blocks in document.
    
    Args:
        document: Document with layout detection results
        pdf_path: Path to source PDF
        dpi: DPI used during layout detection
        
    Returns:
        Document with content populated
    """
    logger.info(f"Extracting content from {pdf_path}")
    
    # Get page dimensions for coordinate conversion
    doc = fitz.open(pdf_path)
    page_heights = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Calculate image height at given DPI
        page_height = page.rect.height * dpi / 72.0
        page_heights.append(page_height)
    doc.close()
    
    # Create figures directory
    figures_dir = stage_dir("extracted/figures", pdf_path)
    
    # Track statistics
    text_blocks = 0
    figure_blocks = 0
    
    # Process each block
    for block in document.blocks:
        page_idx = block.page_index
        
        if block.role in ['Text', 'Title', 'List']:
            # Extract text content
            try:
                text = extract_text_from_bbox(
                    pdf_path,
                    page_idx,
                    block.bbox,
                    page_heights[page_idx]
                )
                
                if text:
                    block.text = text
                    text_blocks += 1
                    logger.debug(f"Extracted text from {block.role} block {block.id}: {len(text)} chars")
                else:
                    logger.warning(f"No text found in {block.role} block {block.id}")
                    
            except Exception as e:
                logger.error(f"Failed to extract text from block {block.id}: {e}")
                
        elif block.role in ['Figure', 'Table']:
            # Extract as image
            try:
                img = extract_figure_image(
                    pdf_path,
                    page_idx,
                    block.bbox,
                    dpi
                )
                
                # Save image
                img_filename = f"{block.role.lower()}_p{page_idx + 1}_{block.id}.png"
                img_path = figures_dir / img_filename
                img.save(img_path, "PNG")
                
                # Store relative path
                block.image_path = f"figures/{img_filename}"
                
                # Generate placeholder text
                position = None
                if hasattr(document, 'reading_order') and page_idx < len(document.reading_order):
                    order = document.reading_order[page_idx]
                    if block.id in order:
                        position = order.index(block.id) + 1
                
                placeholder = f"[{block.role.upper()}"
                if position:
                    placeholder += f" {position}"
                placeholder += f" - See {img_filename}]"
                
                block.text = placeholder
                figure_blocks += 1
                logger.debug(f"Extracted {block.role} block {block.id} as image: {img_path}")
                
            except Exception as e:
                logger.error(f"Failed to extract figure from block {block.id}: {e}")
    
    logger.info(f"Extraction complete: {text_blocks} text blocks, {figure_blocks} figure blocks")
    
    # Update metadata
    document.metadata["extraction"] = {
        "text_blocks": text_blocks,
        "figure_blocks": figure_blocks,
        "figures_dir": str(figures_dir)
    }
    
    return document


def get_document_text(document: Document, include_placeholders: bool = True) -> Dict[int, str]:
    """Get all text content from document in reading order.
    
    Args:
        document: Document with extracted content
        include_placeholders: Whether to include figure/table placeholders
        
    Returns:
        Dict mapping page number to ordered text content
    """
    pages_text = {}
    
    for page_idx in range(document.metadata.get('total_pages', 0)):
        page_elements = []
        
        # Get blocks for this page
        page_blocks = [b for b in document.blocks if b.page_index == page_idx]
        
        # Get reading order
        if hasattr(document, 'reading_order') and page_idx < len(document.reading_order):
            order = document.reading_order[page_idx]
            # Create ID to block mapping
            id_to_block = {b.id: b for b in page_blocks}
            
            # Process in reading order
            for block_id in order:
                if block_id in id_to_block:
                    block = id_to_block[block_id]
                    if block.text:
                        if include_placeholders or block.role not in ['Figure', 'Table']:
                            page_elements.append(block.text)
        else:
            # No reading order, use blocks as-is
            for block in page_blocks:
                if block.text:
                    if include_placeholders or block.role not in ['Figure', 'Table']:
                        page_elements.append(block.text)
        
        if page_elements:
            pages_text[page_idx] = "\n\n".join(page_elements)
    
    return pages_text