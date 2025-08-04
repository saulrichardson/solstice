"""Common PDF processing utilities."""

import logging
from pathlib import Path
from typing import List
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)


def convert_pdf_to_images(pdf_path: Path, cache_dir: str, detection_dpi: int = 400) -> List:
    """Convert PDF to images and save them.
    
    Args:
        pdf_path: Path to PDF file
        cache_dir: Cache directory for storing images
        detection_dpi: DPI for image conversion
        
    Returns:
        List of PIL Images
        
    Raises:
        FileNotFoundError: If PDF doesn't exist
        ValueError: If PDF is invalid or no images extracted
    """
    from .storage.paths import pages_dir
    
    # Validate PDF exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Validate it's a file
    if not pdf_path.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")
        
    page_dir = pages_dir(pdf_path, cache_dir)
    page_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        images = convert_from_path(str(pdf_path), dpi=detection_dpi)
        if not images:
            raise ValueError(f"No images extracted from PDF: {pdf_path}")
            
        for idx, img in enumerate(images):
            img.save(page_dir / f"page-{idx:03}.png")
            
        logger.info(f"Converted {len(images)} pages from {pdf_path.name}")
        return images
        
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        raise


def save_merged_layouts(consolidated_layouts: List, pdf_path: Path, cache_dir: str):
    """Save merged/consolidated layouts to JSON.
    
    Args:
        consolidated_layouts: List of processed box layouts per page
        pdf_path: Path to source PDF
        cache_dir: Cache directory for output
    """
    from .storage.paths import stage_dir, save_json
    
    merged_dir = stage_dir("merged", pdf_path, cache_dir)
    merged_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert Box objects to JSON-serializable format
    merged_data = []
    for page_boxes in consolidated_layouts:
        page_data = []
        for box in page_boxes:
            box_data = {
                "id": box.id,
                "bbox": list(box.bbox),
                "label": box.label,
                "score": box.score,
            }
            # Include lineage information if present
            if hasattr(box, 'source_ids') and box.source_ids:
                box_data["source_ids"] = box.source_ids
            if hasattr(box, 'merge_reason') and box.merge_reason:
                box_data["merge_reason"] = box.merge_reason
            page_data.append(box_data)
        merged_data.append(page_data)
    
    save_json(merged_data, merged_dir / "merged_boxes.json")