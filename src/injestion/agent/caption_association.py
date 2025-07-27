"""Associate captions with figures and tables based on spatial relationships.

This module provides functionality to identify and link caption text boxes
with their corresponding figures or tables, creating semantic groups that
can be passed to appropriate extractors.
"""

from __future__ import annotations

import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field

from .refine_layout import Box


@dataclass
class SemanticGroup:
    """A semantic group containing a figure/table and its associated caption."""
    id: str
    primary_element: Box  # The Figure or Table
    caption: Optional[Box] = None
    group_type: str = ""  # "figure_group" or "table_group"
    confidence: float = 0.0
    
    def __post_init__(self):
        if not self.group_type:
            self.group_type = f"{self.primary_element.label.lower()}_group"


def get_box_center(box: Box) -> Tuple[float, float]:
    """Get the center coordinates of a box."""
    x_center = (box.bbox[0] + box.bbox[2]) / 2
    y_center = (box.bbox[1] + box.bbox[3]) / 2
    return x_center, y_center


def is_below(box1: Box, box2: Box, tolerance: float = 10) -> bool:
    """Check if box1 is below box2."""
    # box1's top edge should be below box2's bottom edge
    return box1.bbox[1] > (box2.bbox[3] - tolerance)


def is_horizontally_aligned(box1: Box, box2: Box, tolerance: float = 50) -> bool:
    """Check if two boxes are horizontally aligned (similar x-coordinates)."""
    x1_center, _ = get_box_center(box1)
    x2_center, _ = get_box_center(box2)
    return abs(x1_center - x2_center) < tolerance


def vertical_distance(box1: Box, box2: Box) -> float:
    """Calculate vertical distance between two boxes."""
    # Distance from bottom of box2 to top of box1
    return box1.bbox[1] - box2.bbox[3]


def is_caption_text(text_box: Box) -> Tuple[bool, float]:
    """Determine if a text box is likely a caption based on content patterns.
    
    Returns:
        Tuple of (is_caption, confidence_score)
    """
    # Common caption patterns
    caption_patterns = [
        r'^(Figure|Fig\.?)\s*\d+',  # Figure 1, Fig. 1, etc.
        r'^(Table|Tab\.?)\s*\d+',   # Table 1, Tab. 1, etc.
        r'^(Chart|Graph)\s*\d+',     # Chart 1, Graph 1, etc.
        r'^(Diagram|Illustration)\s*\d+',
    ]
    
    # In a real implementation, we'd need OCR text. For now, use heuristics.
    # This is a placeholder - in practice, you'd extract text from the box
    # For demonstration, we'll use position and size heuristics
    
    # Captions are typically:
    # 1. Relatively small height (1-3 lines of text)
    # 2. Moderate width (not full page width)
    # 3. Below figures/tables
    
    height = text_box.bbox[3] - text_box.bbox[1]
    width = text_box.bbox[2] - text_box.bbox[0]
    
    # Heuristic scoring
    confidence = 0.5  # Base confidence
    
    # Height check - captions are usually 1-3 lines
    if 20 < height < 100:  # Roughly 1-3 lines at typical font size
        confidence += 0.2
    
    # Width check - captions rarely span full page width
    if 200 < width < 1200:  # Not too narrow, not full width
        confidence += 0.2
    
    # Position check - captions are often centered or slightly indented
    page_width = 1600  # Approximate page width
    left_margin = text_box.bbox[0]
    right_margin = page_width - text_box.bbox[2]
    
    if abs(left_margin - right_margin) < 200:  # Roughly centered
        confidence += 0.1
    
    return confidence > 0.6, confidence


def associate_captions_with_figures(
    boxes: List[Box],
    max_distance: float = 150,
    prefer_below: bool = True
) -> List[SemanticGroup]:
    """Associate caption text boxes with nearby figures and tables.
    
    Args:
        boxes: List of all boxes on the page
        max_distance: Maximum vertical distance to consider for association
        prefer_below: Whether to prefer captions below figures (vs above)
        
    Returns:
        List of semantic groups containing figures/tables with their captions
    """
    # Separate boxes by type
    figures = [b for b in boxes if b.label == "Figure"]
    tables = [b for b in boxes if b.label == "Table"]
    texts = [b for b in boxes if b.label == "Text"]
    
    # Track which boxes have been grouped
    grouped_boxes: Set[str] = set()
    semantic_groups: List[SemanticGroup] = []
    
    # Process figures and tables
    for primary_box in figures + tables:
        if primary_box.id in grouped_boxes:
            continue
            
        best_caption = None
        best_score = 0.0
        
        # Look for potential captions among text boxes
        for text_box in texts:
            if text_box.id in grouped_boxes:
                continue
                
            # Check if this could be a caption
            is_caption, caption_confidence = is_caption_text(text_box)
            if not is_caption:
                continue
            
            # Calculate spatial relationship score
            score = 0.0
            
            # Check if text is below the figure/table
            if is_below(text_box, primary_box):
                distance = vertical_distance(text_box, primary_box)
                
                if distance < max_distance:
                    # Closer is better
                    distance_score = 1.0 - (distance / max_distance)
                    score += distance_score * 0.5
                    
                    # Horizontal alignment bonus
                    if is_horizontally_aligned(text_box, primary_box):
                        score += 0.3
                    
                    # Prefer below if specified
                    if prefer_below:
                        score += 0.2
            
            # Check if text is above (less common but possible)
            elif is_below(primary_box, text_box) and not prefer_below:
                distance = vertical_distance(primary_box, text_box)
                
                if distance < max_distance:
                    distance_score = 1.0 - (distance / max_distance)
                    score += distance_score * 0.3
                    
                    if is_horizontally_aligned(text_box, primary_box):
                        score += 0.2
            
            # Combine with caption confidence
            final_score = score * caption_confidence
            
            if final_score > best_score:
                best_score = final_score
                best_caption = text_box
        
        # Create semantic group
        group = SemanticGroup(
            id=f"group_{primary_box.id}",
            primary_element=primary_box,
            caption=best_caption,
            confidence=best_score
        )
        
        semantic_groups.append(group)
        grouped_boxes.add(primary_box.id)
        
        if best_caption:
            grouped_boxes.add(best_caption.id)
    
    # Add remaining ungrouped elements as standalone groups
    for box in boxes:
        if box.id not in grouped_boxes:
            group = SemanticGroup(
                id=f"group_{box.id}",
                primary_element=box,
                confidence=1.0
            )
            semantic_groups.append(group)
    
    return semantic_groups


def create_extraction_ready_groups(
    boxes: List[Box],
    reading_order: List[str] = None
) -> Dict[str, List[SemanticGroup]]:
    """Create groups ready for extraction, organized by type.
    
    Returns:
        Dictionary with keys:
        - "figure_groups": List of figure+caption groups
        - "table_groups": List of table+caption groups  
        - "text_groups": List of standalone text elements
        - "other_groups": List of other elements
    """
    # First, associate captions
    semantic_groups = associate_captions_with_figures(boxes)
    
    # Organize by type for different extractors
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
    
    # Sort groups by reading order if provided
    if reading_order:
        id_to_order = {id: i for i, id in enumerate(reading_order)}
        
        for group_list in organized.values():
            group_list.sort(
                key=lambda g: id_to_order.get(g.primary_element.id, float('inf'))
            )
    
    return organized


def format_groups_for_extraction(organized_groups: Dict[str, List[SemanticGroup]]) -> Dict:
    """Format semantic groups for downstream extractors.
    
    Returns a dictionary with extraction-ready information.
    """
    extraction_data = {
        "figures": [],
        "tables": [],
        "text_blocks": [],
        "metadata": {
            "total_groups": sum(len(g) for g in organized_groups.values()),
            "has_captions": False
        }
    }
    
    # Process figure groups
    for group in organized_groups["figure_groups"]:
        figure_data = {
            "id": group.id,
            "bbox": group.primary_element.bbox,
            "confidence": group.primary_element.score,
            "has_caption": group.caption is not None,
            "caption_bbox": group.caption.bbox if group.caption else None,
            "group_confidence": group.confidence
        }
        extraction_data["figures"].append(figure_data)
        if group.caption:
            extraction_data["metadata"]["has_captions"] = True
    
    # Process table groups
    for group in organized_groups["table_groups"]:
        table_data = {
            "id": group.id,
            "bbox": group.primary_element.bbox,
            "confidence": group.primary_element.score,
            "has_caption": group.caption is not None,
            "caption_bbox": group.caption.bbox if group.caption else None,
            "group_confidence": group.confidence
        }
        extraction_data["tables"].append(table_data)
        if group.caption:
            extraction_data["metadata"]["has_captions"] = True
    
    # Process text blocks
    for group in organized_groups["text_groups"]:
        text_data = {
            "id": group.id,
            "bbox": group.primary_element.bbox,
            "confidence": group.primary_element.score,
            "type": "standalone_text"
        }
        extraction_data["text_blocks"].append(text_data)
    
    return extraction_data