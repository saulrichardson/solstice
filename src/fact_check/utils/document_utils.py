"""Simple text extraction utilities for fact-checking agents."""

from typing import Dict, Any, List


def get_text(content_json: Dict[str, Any], include_figures: bool = True) -> str:
    """
    Extract text from document JSON in reading order.
    
    Note: Text is already normalized by the ingestion pipeline.
    
    Args:
        content_json: Document content JSON with blocks and reading_order
        include_figures: Whether to include figure/table placeholders
        
    Returns:
        Document text with page separators
    """
    blocks_by_id = {block['id']: block for block in content_json['blocks']}
    reading_order = content_json.get('reading_order', [])
    
    texts = []
    
    for page_idx, page_blocks in enumerate(reading_order):
        # Add page separator (except for first page)
        if page_idx > 0:
            texts.append(f"\n\n[Page {page_idx + 1}]\n")
        
        for block_id in page_blocks:
            block = blocks_by_id.get(block_id)
            if not block:
                continue
            
            # Add text blocks
            if block.get('text'):
                texts.append(block['text'])
            # Add figure/table placeholders if requested
            elif include_figures and block.get('image_path'):
                role = block.get('role', 'FIGURE')
                texts.append(f"[{role.upper()} - See {block['image_path']}]")
    
    return "\n\n".join(texts)





def get_images(content_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get all image blocks (figures and tables) from the document.
    
    Args:
        content_json: Document content JSON
        
    Returns:
        List of image metadata dicts containing:
        - page_index: Page number (0-based)
        - role: Figure or Table
        - image_path: Path to image file
        - bbox: Bounding box coordinates
        - block_id: Block identifier
    """
    blocks_by_id = {block['id']: block for block in content_json['blocks']}
    reading_order = content_json.get('reading_order', [])
    
    images = []
    
    for page_idx, page_blocks in enumerate(reading_order):
        for block_id in page_blocks:
            block = blocks_by_id.get(block_id)
            if not block or not block.get('image_path'):
                continue
            
            images.append({
                'page_index': page_idx,
                'page_number': page_idx + 1,
                'role': block.get('role', 'Figure'),
                'image_path': block['image_path'],
                'bbox': block.get('bbox', []),
                'block_id': block_id
            })
    
    return images
