"""Advanced box merging that handles cross-type overlaps.

This module extends the simple merging to resolve conflicts when merged boxes
of different types end up overlapping.
"""

from __future__ import annotations

import uuid
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass

from .refine_layout import Box
from .merge_boxes import (
    calculate_iou, 
    boxes_overlap, 
    merge_two_boxes,
    merge_overlapping_boxes
)


# Type hierarchy - higher priority types "win" in conflicts
TYPE_PRIORITY = {
    'Title': 5,
    'Table': 4,
    'Figure': 4,
    'List': 3,
    'Text': 2,
    'Unknown': 1
}


def get_overlap_area(box1: Tuple[float, float, float, float], 
                     box2: Tuple[float, float, float, float]) -> float:
    """Calculate the area of overlap between two boxes."""
    x1_inter = max(box1[0], box2[0])
    y1_inter = max(box1[1], box2[1])
    x2_inter = min(box1[2], box2[2])
    y2_inter = min(box1[3], box2[3])
    
    if x2_inter < x1_inter or y2_inter < y1_inter:
        return 0.0
    
    return (x2_inter - x1_inter) * (y2_inter - y1_inter)


def get_box_area(box: Tuple[float, float, float, float]) -> float:
    """Calculate the area of a box."""
    return (box[2] - box[0]) * (box[3] - box[1])


def resolve_cross_type_overlaps(boxes: List[Box], 
                               resolution_strategy: str = "priority") -> List[Box]:
    """Resolve overlaps between boxes of different types.
    
    Args:
        boxes: List of boxes that may have cross-type overlaps
        resolution_strategy: How to resolve conflicts
            - "priority": Higher priority type wins
            - "larger": Larger box wins
            - "confident": Higher confidence score wins
            - "split": Try to split boxes to avoid overlap
            
    Returns:
        List of boxes with cross-type overlaps resolved
    """
    if resolution_strategy == "split":
        return split_overlapping_boxes(boxes)
    
    resolved_boxes = []
    processed = set()
    
    # Sort boxes by priority/size/confidence based on strategy
    if resolution_strategy == "priority":
        sorted_boxes = sorted(boxes, 
                            key=lambda b: TYPE_PRIORITY.get(b.label, 0), 
                            reverse=True)
    elif resolution_strategy == "larger":
        sorted_boxes = sorted(boxes, 
                            key=lambda b: get_box_area(b.bbox), 
                            reverse=True)
    elif resolution_strategy == "confident":
        sorted_boxes = sorted(boxes, 
                            key=lambda b: b.score, 
                            reverse=True)
    else:
        sorted_boxes = boxes
    
    for i, box1 in enumerate(sorted_boxes):
        if i in processed:
            continue
            
        # Check for conflicts with other boxes
        conflicts = []
        for j, box2 in enumerate(sorted_boxes):
            if i == j or j in processed:
                continue
                
            # Different types and significant overlap
            if box1.label != box2.label:
                overlap_area = get_overlap_area(box1.bbox, box2.bbox)
                box2_area = get_box_area(box2.bbox)
                
                # If box2 is significantly covered by box1
                if box2_area > 0 and overlap_area / box2_area > 0.7:
                    conflicts.append(j)
        
        # The current box wins, mark conflicts as processed
        resolved_boxes.append(box1)
        processed.add(i)
        processed.update(conflicts)
        
        # Optionally, we could try to salvage non-overlapping parts
        # of conflicting boxes here
    
    return resolved_boxes


def split_overlapping_boxes(boxes: List[Box]) -> List[Box]:
    """Try to split boxes to avoid cross-type overlaps.
    
    This is a more sophisticated approach that tries to preserve both boxes
    by adjusting their boundaries.
    """
    result = []
    
    for i, box1 in enumerate(boxes):
        current_bbox = list(box1.bbox)
        modified = False
        
        for j, box2 in enumerate(boxes):
            if i == j or box1.label == box2.label:
                continue
                
            overlap_area = get_overlap_area(tuple(current_bbox), box2.bbox)
            if overlap_area > 0:
                # Determine the best way to split
                # This is a simple heuristic - could be made more sophisticated
                
                # Get overlap boundaries
                x1_inter = max(current_bbox[0], box2.bbox[0])
                y1_inter = max(current_bbox[1], box2.bbox[1])
                x2_inter = min(current_bbox[2], box2.bbox[2])
                y2_inter = min(current_bbox[3], box2.bbox[3])
                
                # Decide based on type priority
                box1_priority = TYPE_PRIORITY.get(box1.label, 0)
                box2_priority = TYPE_PRIORITY.get(box2.label, 0)
                
                if box2_priority > box1_priority:
                    # Try to shrink box1 to avoid box2
                    # Simple approach: adjust the boundary that creates smallest change
                    adjustments = [
                        (x2_inter - current_bbox[0], (x2_inter, current_bbox[1], current_bbox[2], current_bbox[3])),
                        (current_bbox[2] - x1_inter, (current_bbox[0], current_bbox[1], x1_inter, current_bbox[3])),
                        (y2_inter - current_bbox[1], (current_bbox[0], y2_inter, current_bbox[2], current_bbox[3])),
                        (current_bbox[3] - y1_inter, (current_bbox[0], current_bbox[1], current_bbox[2], y1_inter))
                    ]
                    
                    # Pick adjustment that preserves most area
                    valid_adjustments = [(area, bbox) for area, bbox in adjustments 
                                       if area > 0 and get_box_area(bbox) > 0.3 * get_box_area(current_bbox)]
                    
                    if valid_adjustments:
                        _, new_bbox = max(valid_adjustments, key=lambda x: get_box_area(x[1]))
                        current_bbox = list(new_bbox)
                        modified = True
        
        # Create adjusted box
        adjusted_box = Box(
            id=box1.id if not modified else str(uuid.uuid4())[:8],
            bbox=tuple(current_bbox),
            label=box1.label,
            score=box1.score
        )
        result.append(adjusted_box)
    
    return result


def merge_and_resolve_conflicts(
    boxes: List[Box],
    merge_same_type: bool = True,
    iou_threshold: float = 0.1,
    resolution_strategy: str = "priority"
) -> List[Box]:
    """Complete pipeline: merge same-type boxes, then resolve cross-type conflicts.
    
    Args:
        boxes: Input boxes
        merge_same_type: Whether to merge overlapping same-type boxes first
        iou_threshold: Threshold for same-type merging
        resolution_strategy: How to handle cross-type overlaps
        
    Returns:
        Processed boxes with both same-type merging and conflict resolution
    """
    # Step 1: Merge same-type overlapping boxes
    if merge_same_type:
        merged = merge_overlapping_boxes(boxes, iou_threshold=iou_threshold)
    else:
        merged = boxes
    
    # Step 2: Resolve any cross-type overlaps created by merging
    resolved = resolve_cross_type_overlaps(merged, resolution_strategy)
    
    return resolved


def analyze_cross_type_overlaps(boxes: List[Box]) -> List[Dict]:
    """Analyze and report cross-type overlaps in the layout.
    
    Returns list of overlap information for debugging.
    """
    overlaps = []
    
    for i, box1 in enumerate(boxes):
        for j, box2 in enumerate(boxes):
            if i >= j or box1.label == box2.label:
                continue
                
            overlap_area = get_overlap_area(box1.bbox, box2.bbox)
            if overlap_area > 0:
                box1_area = get_box_area(box1.bbox)
                box2_area = get_box_area(box2.bbox)
                
                overlap_info = {
                    'box1_id': box1.id,
                    'box1_label': box1.label,
                    'box1_area': box1_area,
                    'box2_id': box2.id,
                    'box2_label': box2.label,
                    'box2_area': box2_area,
                    'overlap_area': overlap_area,
                    'overlap_pct_box1': overlap_area / box1_area if box1_area > 0 else 0,
                    'overlap_pct_box2': overlap_area / box2_area if box2_area > 0 else 0,
                    'iou': calculate_iou(box1.bbox, box2.bbox)
                }
                overlaps.append(overlap_info)
    
    return sorted(overlaps, key=lambda x: x['overlap_area'], reverse=True)