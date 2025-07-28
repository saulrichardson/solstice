"""Reading order detection."""

from typing import List

from ..models.box import Box


def determine_reading_order_simple(boxes: List[Box], page_width: float = 1600) -> List[str]:
    """
    Simple reading order: left side first (top to bottom), then right side (top to bottom).
    
    Args:
        boxes: All boxes on the page
        page_width: Width of the page
        
    Returns:
        List of box IDs in reading order
    """
    if not boxes:
        return []
    
    # Find page midpoint
    midpoint = page_width / 2
    
    # Define a buffer zone around the midpoint to handle edge cases
    buffer = 50  # pixels
    
    # Split boxes into left and right groups
    left_boxes = []
    right_boxes = []
    
    for box in boxes:
        # Check if box is clearly in left column
        if box.bbox[0] < midpoint - buffer:
            left_boxes.append(box)
        # Check if box is clearly in right column
        elif box.bbox[0] > midpoint + buffer:
            right_boxes.append(box)
        else:
            # Box is in the buffer zone - decide based on its center
            box_center = (box.bbox[0] + box.bbox[2]) / 2
            if box_center < midpoint:
                left_boxes.append(box)
            else:
                right_boxes.append(box)
    
    # Sort each group by vertical position
    left_boxes.sort(key=lambda b: b.bbox[1])
    right_boxes.sort(key=lambda b: b.bbox[1])
    
    # Build reading order: left first, then right
    reading_order = []
    reading_order.extend([b.id for b in left_boxes])
    reading_order.extend([b.id for b in right_boxes])
    
    return reading_order