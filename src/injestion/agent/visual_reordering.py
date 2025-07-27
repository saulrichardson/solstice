"""Visual reordering for complex layouts with figures and tables.

This module provides visual-based reordering when the standard column-based
ordering might fail due to complex layouts with figures, tables, and captions
that span columns.
"""

from __future__ import annotations

import json
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

from .llm_client_chat import call_llm
from .refine_layout import Box

logger = logging.getLogger(__name__)


class LLMClient:
    """Simple wrapper for LLM operations with vision support."""
    
    def __init__(self, api_key: str = None):
        # API key is handled by the centralized client
        pass
    
    def generate_with_image(
        self, 
        prompt: str, 
        image_base64: str, 
        temperature: float = 0.1,
        response_format: Dict[str, str] = None
    ) -> str:
        """Generate response with image input."""
        user_content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "url": f"data:image/png;base64,{image_base64}",
                "detail": "high"
            }
        ]
        
        return call_llm(
            system_prompt="You are a document layout analysis expert.",
            user_content=user_content,
            model="gpt-4o-mini",  # Vision-capable model
            temperature=temperature
        )


def has_complex_elements(boxes: List[Box]) -> bool:
    """Check if the page has figures or tables that might need visual reordering.
    
    Args:
        boxes: List of layout boxes
        
    Returns:
        True if figures or tables are present
    """
    return any(box.label in ['Figure', 'Table'] for box in boxes)


def create_annotated_visualization(
    page_image: Image.Image,
    boxes: List[Box],
    current_order: List[str]
) -> Image.Image:
    """Create an annotated image showing boxes with their current reading order.
    
    Args:
        page_image: Original page image
        boxes: List of layout boxes
        current_order: Current reading order (list of box IDs)
        
    Returns:
        Annotated PIL Image
    """
    # Create a copy to draw on
    annotated = page_image.copy()
    draw = ImageDraw.Draw(annotated)
    
    # Try to use a default font, fallback to PIL default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # Create ID to position mapping
    id_to_pos = {box_id: i + 1 for i, box_id in enumerate(current_order)}
    id_to_box = {box.id: box for box in boxes}
    
    # Color map for different element types
    color_map = {
        'Text': 'blue',
        'Title': 'red',
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    # Draw boxes with numbers
    for box in boxes:
        x1, y1, x2, y2 = box.bbox
        color = color_map.get(box.label, 'gray')
        
        # Draw rectangle
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        
        # Add reading order number
        pos = id_to_pos.get(box.id, 0)
        if pos > 0:
            # Draw number in a circle
            cx, cy = x1 + 30, y1 + 30
            radius = 20
            draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], 
                        fill='yellow', outline='red', width=2)
            
            # Center the text
            text = str(pos)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text((cx - text_width//2, cy - text_height//2), 
                     text, fill='red', font=font)
            
            # Add label type
            draw.text((x1 + 5, y1 + 60), box.label, fill=color, font=small_font)
    
    return annotated


def get_visual_reading_order(
    page_image: Image.Image,
    boxes: List[Box],
    current_order: List[str],
    llm_client: LLMClient
) -> Optional[List[str]]:
    """Use vision model to determine correct reading order for complex layouts.
    
    Args:
        page_image: Original page image
        boxes: List of layout boxes
        current_order: Current reading order
        llm_client: LLM client for vision analysis
        
    Returns:
        New reading order if changes needed, None if current order is good
    """
    # Create annotated visualization
    annotated_image = create_annotated_visualization(page_image, boxes, current_order)
    
    # Convert to base64
    buffered = io.BytesIO()
    annotated_image.save(buffered, format="PNG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Prepare element descriptions
    id_to_box = {box.id: box for box in boxes}
    elements_desc = []
    for i, box_id in enumerate(current_order):
        box = id_to_box[box_id]
        elements_desc.append(f"{i+1}: {box.label} at position ({box.bbox[0]}, {box.bbox[1]})")
    
    prompt = f"""You are analyzing the reading order of a document page with figures and tables.
The image shows numbered boxes representing different elements:
- Red boxes: Titles
- Blue boxes: Text
- Orange boxes: Figures
- Purple boxes: Tables
- Green boxes: Lists

Current reading order:
{chr(10).join(elements_desc)}

Please analyze if this reading order is correct for natural document flow. Pay special attention to:
1. Figure/table captions that should immediately follow their associated figure/table
2. Captions that span across columns (read left-to-right across columns)
3. Multi-column text that should be read top-to-bottom within each column

If the current order is correct, respond with this JSON:
{{"order_correct": true}}

If reordering is needed, provide the corrected sequence as a list of numbers in JSON format:
{{"order_correct": false, "new_order": [1, 2, 3, ...]}}

Focus especially on figure/table and caption relationships. Always respond with valid JSON."""

    try:
        response = llm_client.generate_with_image(
            prompt=prompt,
            image_base64=image_base64,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response)
        
        if not result.get('order_correct', True):
            new_order = result.get('new_order', [])
            if new_order and len(new_order) == len(current_order):
                # Convert position numbers back to IDs
                reordered_ids = []
                for pos in new_order:
                    if 1 <= pos <= len(current_order):
                        reordered_ids.append(current_order[pos - 1])
                
                if len(reordered_ids) == len(current_order):
                    logger.info(f"Visual analysis suggests reordering: {new_order}")
                    return reordered_ids
        
        logger.info("Visual analysis confirms current order is correct")
        return None
        
    except Exception as e:
        logger.error(f"Error in visual reordering: {e}")
        return None


def determine_semantic_order_with_vision(
    boxes: List[Box],
    page_image: Optional[Image.Image] = None,
    page_width: float = 1600,
    llm_client: Optional[LLMClient] = None
) -> List[str]:
    """Enhanced semantic ordering that uses vision for complex layouts.
    
    Args:
        boxes: List of boxes to order
        page_image: Optional page image for visual analysis
        page_width: Width of the page for column detection
        llm_client: Optional LLM client for vision analysis
        
    Returns:
        List of box IDs in reading order
    """
    # First, use the standard column-based ordering
    from ..pipeline_extraction import determine_semantic_order
    initial_order = determine_semantic_order(boxes, page_width)
    
    # Check if we need visual reordering
    if (page_image is not None and 
        llm_client is not None and 
        has_complex_elements(boxes)):
        
        logger.info("Page contains figures/tables - checking with visual analysis")
        
        # Get visual suggestions
        new_order = get_visual_reading_order(
            page_image, boxes, initial_order, llm_client
        )
        
        if new_order:
            return new_order
    
    return initial_order


def create_debug_visualization(
    page_image: Image.Image,
    boxes: List[Box],
    original_order: List[str],
    new_order: List[str],
    output_path: str
) -> None:
    """Create a side-by-side comparison of original and new reading orders.
    
    Args:
        page_image: Original page image
        boxes: List of layout boxes
        original_order: Original reading order
        new_order: New reading order after visual analysis
        output_path: Path to save the comparison image
    """
    # Create two annotated versions
    original_annotated = create_annotated_visualization(page_image, boxes, original_order)
    new_annotated = create_annotated_visualization(page_image, boxes, new_order)
    
    # Create side-by-side image
    width = page_image.width
    height = page_image.height
    combined = Image.new('RGB', (width * 2 + 20, height + 60), 'white')
    
    # Paste images
    combined.paste(original_annotated, (0, 30))
    combined.paste(new_annotated, (width + 20, 30))
    
    # Add labels
    draw = ImageDraw.Draw(combined)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font = ImageFont.load_default()
    
    draw.text((width // 2 - 100, 5), "Original Order", fill='black', font=font)
    draw.text((width + width // 2 - 100 + 20, 5), "Corrected Order", fill='black', font=font)
    
    # Save
    combined.save(output_path)
    logger.info(f"Saved comparison visualization to {output_path}")