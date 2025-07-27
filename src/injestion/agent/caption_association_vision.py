"""Vision-based caption association using LLM with image understanding.

This module uses OpenAI's vision capabilities to intelligently associate
captions with figures and tables by understanding the visual layout and
reading the actual text content.
"""

from __future__ import annotations

import base64
import io
import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from .refine_layout import Box
from .caption_association import SemanticGroup, get_box_center
from .llm_client_chat import call_llm


def encode_image_to_base64(image: Image.Image) -> str:
    """Encode PIL image to base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def create_annotated_image(
    page_image: Image.Image,
    boxes: List[Box],
    highlight_figures_tables: bool = True
) -> Tuple[Image.Image, Dict[str, Box]]:
    """Create an annotated image with bounding boxes and IDs for vision analysis.
    
    Args:
        page_image: Original page image
        boxes: List of boxes to annotate
        highlight_figures_tables: Whether to highlight figures/tables differently
        
    Returns:
        Tuple of (annotated_image, id_to_box_mapping)
    """
    # Create a copy to annotate
    annotated = page_image.copy()
    draw = ImageDraw.Draw(annotated)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        font = ImageFont.load_default()
    
    # Create ID mapping
    id_map = {}
    
    # Color scheme
    colors = {
        'Figure': 'orange',
        'Table': 'purple',
        'Text': 'blue',
        'Title': 'red',
        'List': 'green'
    }
    
    for i, box in enumerate(boxes):
        # Create simple ID for vision model
        simple_id = f"{box.label[0]}{i}"  # F0, T1, etc.
        id_map[simple_id] = box
        
        # Get color
        color = colors.get(box.label, 'gray')
        
        # Draw bounding box
        x1, y1, x2, y2 = box.bbox
        
        # Highlight figures and tables with thicker lines
        width = 3 if box.label in ['Figure', 'Table'] else 2
        
        # Draw rectangle
        draw.rectangle(
            [(x1, y1), (x2, y2)],
            outline=color,
            width=width
        )
        
        # Add label with ID
        label_text = f"{simple_id}: {box.label}"
        
        # Draw label background
        text_bbox = draw.textbbox((x1, y1 - 25), label_text, font=font)
        draw.rectangle(text_bbox, fill='white', outline=color)
        draw.text((x1, y1 - 25), label_text, fill=color, font=font)
    
    return annotated, id_map


def associate_captions_with_vision(
    page_image: Image.Image,
    boxes: List[Box],
    debug: bool = False
) -> List[SemanticGroup]:
    """Use vision LLM to associate captions with figures and tables.
    
    Args:
        page_image: The page image
        boxes: List of detected boxes
        debug: Whether to save debug visualizations
        
    Returns:
        List of semantic groups with vision-based associations
    """
    # Create annotated image
    annotated_image, id_map = create_annotated_image(page_image, boxes)
    
    # Save debug image if requested
    if debug:
        annotated_image.save("debug_vision_annotated.png")
    
    # Encode image
    image_base64 = encode_image_to_base64(annotated_image)
    
    # Create prompt for vision model
    prompt = """Analyze this annotated document page to associate captions with figures and tables.

Each bounding box has an ID (like F0, T1, t2) where:
- F = Figure
- T = Table  
- t = Text
- L = List
- etc.

Your task:
1. Identify which text boxes contain captions (look for patterns like "Figure 1:", "Table 1:", etc.)
2. Match each caption to its corresponding figure or table based on:
   - Proximity (captions are usually directly below or above)
   - Text content (caption numbers should match figure/table context)
   - Visual alignment
   
Return a JSON object with the following structure:
{
    "associations": [
        {
            "element_id": "F0",  // The figure or table ID
            "caption_id": "t3",  // The text box containing its caption
            "confidence": 0.95,  // How confident you are (0-1)
            "reasoning": "Text box t3 contains 'Figure 1:' and is directly below figure F0"
        }
    ],
    "unmatched_figures_tables": ["F1", "T2"],  // Any figures/tables without captions
    "identified_captions": ["t3", "t5"]  // All text boxes identified as captions
}"""

    # Create content for vision API
    content = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url", 
            "url": f"data:image/png;base64,{image_base64}",
            "detail": "high"
        }
    ]
    
    # Call vision model
    response_text = call_llm(
        system_prompt="You are a document layout analysis expert. Analyze images and return JSON responses.",
        user_content=content,
        model="gpt-4o",  # Use vision-capable model
        temperature=0.1,
        max_tokens=2000
    )
    
    # Parse response
    try:
        response = json.loads(response_text)
        associations_data = response.get("associations", [])
        
        # Debug: print response
        print(f"\nVision API Response:")
        print(json.dumps(response, indent=2))
        
    except json.JSONDecodeError:
        print(f"Failed to parse JSON response: {response_text}")
        associations_data = []
    
    # Create semantic groups
    semantic_groups = []
    associated_boxes = set()
    
    # Process associations
    for assoc in associations_data:
        element_id = assoc.get("element_id")
        caption_id = assoc.get("caption_id")
        confidence = assoc.get("confidence", 0.0)
        
        if element_id in id_map and caption_id in id_map:
            element_box = id_map[element_id]
            caption_box = id_map[caption_id]
            
            group = SemanticGroup(
                id=f"group_{element_box.id}",
                primary_element=element_box,
                caption=caption_box,
                confidence=confidence
            )
            
            semantic_groups.append(group)
            associated_boxes.add(element_box.id)
            associated_boxes.add(caption_box.id)
    
    # Add unmatched elements as standalone groups
    for box in boxes:
        if box.id not in associated_boxes:
            group = SemanticGroup(
                id=f"group_{box.id}",
                primary_element=box,
                confidence=1.0
            )
            semantic_groups.append(group)
    
    return semantic_groups


def create_extraction_ready_groups_vision(
    page_image: Image.Image,
    boxes: List[Box],
    reading_order: List[str] = None,
    debug: bool = False
) -> Dict[str, List[SemanticGroup]]:
    """Create vision-based extraction-ready groups.
    
    This is a drop-in replacement for create_extraction_ready_groups that uses
    vision understanding instead of heuristics.
    """
    # Get vision-based associations
    semantic_groups = associate_captions_with_vision(
        page_image, boxes, debug=debug
    )
    
    # Organize by type (same as original)
    organized = {
        "figure_groups": [],
        "table_groups": [],
        "text_groups": [],
        "other_groups": []
    }
    
    for group in semantic_groups:
        if group.primary_element.label == "Figure":
            organized["figure_groups"].append(group)
        elif group.primary_element.label == "Table":
            organized["table_groups"].append(group)
        elif group.primary_element.label == "Text":
            organized["text_groups"].append(group)
        else:
            organized["other_groups"].append(group)
    
    # Sort by reading order if provided
    if reading_order:
        id_to_order = {id: i for i, id in enumerate(reading_order)}
        
        for group_list in organized.values():
            group_list.sort(
                key=lambda g: id_to_order.get(g.primary_element.id, float('inf'))
            )
    
    return organized