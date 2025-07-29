"""Debug utility to track box coordinate transformations."""

from typing import List, Tuple
from .box import Box


def log_box_transformation(boxes_before: List[Box], boxes_after: List[Box], operation: str) -> None:
    """Log how boxes changed during a transformation.
    
    Args:
        boxes_before: Original boxes
        boxes_after: Transformed boxes  
        operation: Name of the operation performed
    """
    print(f"\n=== {operation} ===")
    
    # Match boxes by ID
    before_dict = {box.id: box for box in boxes_before}
    after_dict = {box.id: box for box in boxes_after}
    
    for box_id in before_dict:
        if box_id in after_dict:
            before = before_dict[box_id]
            after = after_dict[box_id]
            
            x1_b, y1_b, x2_b, y2_b = before.bbox
            x1_a, y1_a, x2_a, y2_a = after.bbox
            
            # Calculate shifts
            left_shift = x1_a - x1_b
            top_shift = y1_a - y1_b
            right_shift = x2_a - x2_b
            bottom_shift = y2_a - y2_b
            
            if (left_shift != 0 or top_shift != 0 or right_shift != 0 or bottom_shift != 0):
                print(f"Box {box_id} ({before.label}):")
                print(f"  Before: ({x1_b:.1f}, {y1_b:.1f}, {x2_b:.1f}, {y2_b:.1f})")
                print(f"  After:  ({x1_a:.1f}, {y1_a:.1f}, {x2_a:.1f}, {y2_a:.1f})")
                print(f"  Shifts: left={left_shift:.1f}, top={top_shift:.1f}, right={right_shift:.1f}, bottom={bottom_shift:.1f}")
                
                # Check for asymmetric expansion
                if abs(left_shift) != abs(right_shift) or abs(top_shift) != abs(bottom_shift):
                    print(f"  WARNING: Asymmetric change detected!")


def compare_box_centers(boxes1: List[Box], boxes2: List[Box]) -> None:
    """Compare the centers of matching boxes to detect shifts."""
    print("\n=== Center Point Analysis ===")
    
    dict1 = {box.id: box for box in boxes1}
    dict2 = {box.id: box for box in boxes2}
    
    for box_id in dict1:
        if box_id in dict2:
            box1 = dict1[box_id]
            box2 = dict2[box_id]
            
            # Calculate centers
            x1_1, y1_1, x2_1, y2_1 = box1.bbox
            center1_x = (x1_1 + x2_1) / 2
            center1_y = (y1_1 + y2_1) / 2
            
            x1_2, y1_2, x2_2, y2_2 = box2.bbox
            center2_x = (x1_2 + x2_2) / 2
            center2_y = (y1_2 + y2_2) / 2
            
            # Calculate shift
            shift_x = center2_x - center1_x
            shift_y = center2_y - center1_y
            
            if abs(shift_x) > 0.1 or abs(shift_y) > 0.1:
                print(f"Box {box_id} ({box1.label}): center shifted by ({shift_x:.1f}, {shift_y:.1f})")