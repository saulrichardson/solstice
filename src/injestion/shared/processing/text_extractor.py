"""Native PDF text extraction using bounding boxes from layout detection."""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image
import numpy as np

from src.interfaces import Document, Block
from ..storage.paths import stage_dir
from .text_extractors import TextExtractor, PyMuPDFExtractor

logger = logging.getLogger(__name__)

def get_text_extractor() -> TextExtractor:
    """Get the PyMuPDF text extractor instance.
    
    Returns:
        PyMuPDFExtractor instance
    """
    # Always create a fresh instance to avoid state pollution
    # PyMuPDF extractor is lightweight and stateless
    logger.debug("Creating new PyMuPDF text extractor")
    return PyMuPDFExtractor()


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
    extractor = get_text_extractor()
    result = extractor.extract_text_from_bbox(pdf_path, page_num, bbox, page_height)
    return result.text


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
    extractor = get_text_extractor()
    return extractor.extract_figure_image(pdf_path, page_num, bbox, dpi)


def extract_document_content(
    document: Document,
    pdf_path: Path,
    dpi: int,
    cache_dir: str
) -> Document:
    """Extract text and figure content for all blocks in document.
    
    Args:
        document: Document with layout detection results
        pdf_path: Path to source PDF
        dpi: DPI used during layout detection
        
    Returns:
        Document with content populated
    """
    logger.info(f"Extracting content from {pdf_path} using PyMuPDF extractor")
    
    # Open PDF - will raise if file cannot be opened
    doc = fitz.open(pdf_path)
    
    # Get page dimensions for coordinate conversion
    page_heights = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # We MUST use the same DPI that was used for detection
        # Using any other DPI will cause coordinate misalignment
        # Detection DPI is passed in and stored in document metadata
        page_height = page.rect.height * dpi / 72.0
        page_heights.append(page_height)
        
        # Validate page dimensions
        if page_height <= 0 or page.rect.width <= 0:
            logger.error(f"Invalid page dimensions for page {page_num}: {page.rect}")
            raise ValueError(f"Invalid page dimensions on page {page_num}")
        
        logger.debug(f"Page {page_num}: PDF height={page.rect.height}, Image height at {dpi}dpi={page_height}")
    
    doc.close()
    
    # Create figures directory
    figures_dir = stage_dir("extracted/figures", pdf_path, cache_dir)
    
    # Track statistics
    text_blocks = 0
    figure_blocks = 0
    
    # Process each block
    for block in document.blocks:
        page_idx = block.page_index
        
        if block.role in ['Text', 'Title', 'List']:
            # Extract text content
            result = get_text_extractor().extract_text_from_bbox(
                pdf_path,
                page_idx,
                block.bbox,
                page_heights[page_idx]
            )
            
            if result.text:
                block.text = result.text
                text_blocks += 1
                logger.debug(f"Extracted text from {block.role} block {block.id}: {len(result.text)} chars")
                if result.confidence is not None:
                    block.metadata['extraction_confidence'] = result.confidence
                # Store extraction metadata if available
                if result.metadata:
                    block.metadata['extraction'] = result.metadata
            else:
                # No text found - this is not an error, just empty
                block.text = ""
                block.metadata['extraction_status'] = 'empty'
                logger.debug(f"No text found in {block.role} block {block.id}")
                
        elif block.role in ['Figure', 'Table']:
            # Extract as image
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
