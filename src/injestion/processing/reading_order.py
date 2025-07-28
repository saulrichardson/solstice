"""Simple reading order detection based on left/right positioning."""

from typing import List, Tuple


class Box:
    """Box class to match the one used in the pipeline."""
    def __init__(self, id: str, bbox: Tuple[float, float, float, float], label: str, score: float):
        self.id = id
        self.bbox = bbox
        self.label = label
        self.score = score
        
    @property
    def x1(self): return self.bbox[0]
    
    @property
    def y1(self): return self.bbox[1]
    
    @property
    def x2(self): return self.bbox[2]
    
    @property
    def y2(self): return self.bbox[3]
    
    @property
    def center_x(self): return (self.x1 + self.x2) / 2
    
    @property
    def center_y(self): return (self.y1 + self.y2) / 2


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
    
    # Split boxes into left and right groups based on left edge position
    left_boxes = []
    right_boxes = []
    
    for box in boxes:
        if box.x1 < midpoint:
            left_boxes.append(box)
        else:
            right_boxes.append(box)
    
    # Sort each group by vertical position
    left_boxes.sort(key=lambda b: b.y1)
    right_boxes.sort(key=lambda b: b.y1)
    
    # Build reading order: left first, then right
    reading_order = []
    reading_order.extend([b.id for b in left_boxes])
    reading_order.extend([b.id for b in right_boxes])
    
    return reading_order