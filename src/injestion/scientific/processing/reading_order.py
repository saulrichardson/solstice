"""Reading order detection."""

from typing import List

from ...shared.processing.box import Box


def determine_reading_order_simple(boxes: List[Box], page_width: float, page_height: float) -> List[str]:
    """
    Simple reading order: left side first (top to bottom), then right side (top to bottom),
    with special handling for full-width elements at the bottom (e.g., footnotes).
    
    Args:
        boxes: All boxes on the page
        page_width: Width of the page
        page_height: Height of the page
        
    Returns:
        List of box IDs in reading order
    """
    if not boxes:
        return []
    
    # Find page midpoint
    midpoint = page_width / 2
    
    # Define a buffer zone around the midpoint to handle edge cases
    buffer = 50  # pixels
    
    # Identify full-width bottom elements (footnotes, page numbers, etc.)
    full_width_threshold = page_width * 0.75  # Elements spanning 75%+ of page width
    bottom_threshold = page_height * 0.8  # Elements in bottom 20% of page
    
    full_width_bottom = []
    regular_boxes = []
    
    for box in boxes:
        box_width = box.bbox[2] - box.bbox[0]
        box_top = box.bbox[1]
        
        # Check if this is a full-width element at the bottom
        if box_width >= full_width_threshold and box_top >= bottom_threshold:
            full_width_bottom.append(box)
        else:
            regular_boxes.append(box)
    
    # Process regular boxes with the column logic
    left_boxes = []
    right_boxes = []
    
    for box in regular_boxes:
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
    full_width_bottom.sort(key=lambda b: b.bbox[1])  # Sort footnotes by position too
    
    # Build reading order: left first, then right, then full-width bottom elements
    reading_order = []
    reading_order.extend([b.id for b in left_boxes])
    reading_order.extend([b.id for b in right_boxes])
    reading_order.extend([b.id for b in full_width_bottom])
    
    return reading_order