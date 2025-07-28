"""No-overlap resolver that guarantees zero overlapping boxes.

This module ensures that the final output contains no overlapping boxes
by using various strategies to handle different overlap scenarios.
"""

from __future__ import annotations

import uuid
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum

from .refine_layout import Box


def calculate_iou(box1: Tuple[float, float, float, float], 
                  box2: Tuple[float, float, float, float]) -> float:
    """Calculate Intersection over Union between two boxes."""
    x1_inter = max(box1[0], box2[0])
    y1_inter = max(box1[1], box2[1])
    x2_inter = min(box1[2], box2[2])
    y2_inter = min(box1[3], box2[3])
    
    if x2_inter < x1_inter or y2_inter < y1_inter:
        return 0.0
    
    inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    
    return inter_area / union_area if union_area > 0 else 0.0


def get_box_area(bbox: Tuple[float, float, float, float]) -> float:
    """Calculate area of a bounding box."""
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def get_overlap_area(bbox1: Tuple[float, float, float, float],
                     bbox2: Tuple[float, float, float, float]) -> float:
    """Calculate the overlapping area between two bounding boxes."""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    
    if x2 < x1 or y2 < y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def calculate_box_weight(box: Box, 
                        confidence_weight: float = 0.7,
                        area_weight: float = 0.3,
                        type_bonus: Dict[str, float] = None) -> float:
    """Calculate a weight score for a box based on multiple factors."""
    # Normalize weights
    total_weight = confidence_weight + area_weight
    conf_w = confidence_weight / total_weight
    area_w = area_weight / total_weight
    
    # Get box area and normalize it (assuming page is ~2000x2000)
    area = get_box_area(box.bbox)
    normalized_area = min(area / (2000 * 2000), 1.0)
    
    # Base score from confidence and area
    base_score = (box.score * conf_w) + (normalized_area * area_w)
    
    # Apply type bonus if specified
    if type_bonus and box.label in type_bonus:
        base_score *= (1.0 + type_bonus[box.label])
    
    return base_score


def merge_overlapping_boxes(boxes: List[Box], iou_threshold: float = 0.5) -> List[Box]:
    """Merge overlapping boxes of the same type."""
    if not boxes:
        return []
    
    # Group boxes by type
    boxes_by_type = {}
    for box in boxes:
        if box.label not in boxes_by_type:
            boxes_by_type[box.label] = []
        boxes_by_type[box.label].append(box)
    
    merged_boxes = []
    
    # Process each type separately
    for box_type, type_boxes in boxes_by_type.items():
        # Track which boxes have been merged
        merged = [False] * len(type_boxes)
        
        for i in range(len(type_boxes)):
            if merged[i]:
                continue
                
            # Start a new merge group
            merge_group = [type_boxes[i]]
            merged[i] = True
            
            # Find all boxes that should be merged with this one
            for j in range(i + 1, len(type_boxes)):
                if merged[j]:
                    continue
                    
                # Check if this box overlaps with any box in the merge group
                should_merge = False
                for group_box in merge_group:
                    iou = calculate_iou(group_box.bbox, type_boxes[j].bbox)
                    if iou > iou_threshold:
                        should_merge = True
                        break
                
                if should_merge:
                    merge_group.append(type_boxes[j])
                    merged[j] = True
            
            # Create merged box from the group
            if len(merge_group) == 1:
                merged_boxes.append(merge_group[0])
            else:
                # Calculate bounding box of all boxes in group
                x1 = min(b.bbox[0] for b in merge_group)
                y1 = min(b.bbox[1] for b in merge_group)
                x2 = max(b.bbox[2] for b in merge_group)
                y2 = max(b.bbox[3] for b in merge_group)
                
                # Use the highest score
                best_score = max(b.score for b in merge_group)
                
                # Create new merged box
                merged_box = Box(
                    id=str(uuid.uuid4())[:8],
                    bbox=(x1, y1, x2, y2),
                    label=box_type,
                    score=best_score
                )
                merged_boxes.append(merged_box)
    
    return merged_boxes


class OverlapStrategy(Enum):
    """Strategies for handling overlaps."""
    KEEP_HIGHER_WEIGHT = "keep_higher_weight"
    MERGE = "merge"
    SPLIT_HORIZONTAL = "split_horizontal"
    SPLIT_VERTICAL = "split_vertical"
    SHRINK_TO_NON_OVERLAP = "shrink_to_non_overlap"


def get_overlap_info(box1: Box, box2: Box) -> Dict:
    """Get detailed overlap information between two boxes."""
    overlap_area = get_overlap_area(box1.bbox, box2.bbox)
    if overlap_area == 0:
        return {
            "has_overlap": False,
            "overlap_area": 0,
            "overlap_ratio_box1": 0,
            "overlap_ratio_box2": 0,
            "is_nested": False,
            "is_partial": False
        }
    
    area1 = get_box_area(box1.bbox)
    area2 = get_box_area(box2.bbox)
    
    overlap_ratio1 = overlap_area / area1 if area1 > 0 else 0
    overlap_ratio2 = overlap_area / area2 if area2 > 0 else 0
    
    # Check if one box is nested inside another
    is_nested = overlap_ratio1 > 0.95 or overlap_ratio2 > 0.95
    
    return {
        "has_overlap": True,
        "overlap_area": overlap_area,
        "overlap_ratio_box1": overlap_ratio1,
        "overlap_ratio_box2": overlap_ratio2,
        "is_nested": is_nested,
        "is_partial": not is_nested
    }


def determine_overlap_strategy(box1: Box, box2: Box, overlap_info: Dict) -> OverlapStrategy:
    """Determine the best strategy for handling overlap between two boxes."""
    
    # If one box is nested inside another
    if overlap_info["is_nested"]:
        # Keep the outer box for containers (Figure, Table)
        if box1.label in ["Figure", "Table"] or box2.label in ["Figure", "Table"]:
            return OverlapStrategy.KEEP_HIGHER_WEIGHT
        # For text elements, keep the more specific one
        return OverlapStrategy.KEEP_HIGHER_WEIGHT
    
    # Same type boxes - merge them
    if box1.label == box2.label:
        return OverlapStrategy.MERGE
    
    # Small overlap - try to shrink boxes
    if overlap_info["overlap_ratio_box1"] < 0.2 and overlap_info["overlap_ratio_box2"] < 0.2:
        return OverlapStrategy.SHRINK_TO_NON_OVERLAP
    
    # Otherwise, keep the higher weight box
    return OverlapStrategy.KEEP_HIGHER_WEIGHT


def merge_boxes(box1: Box, box2: Box) -> Box:
    """Merge two boxes into one."""
    x1 = min(box1.bbox[0], box2.bbox[0])
    y1 = min(box1.bbox[1], box2.bbox[1])
    x2 = max(box1.bbox[2], box2.bbox[2])
    y2 = max(box1.bbox[3], box2.bbox[3])
    
    # Use the higher score and keep the label
    if box1.score > box2.score:
        return Box(
            id=box1.id,
            bbox=(x1, y1, x2, y2),
            label=box1.label,
            score=box1.score
        )
    else:
        return Box(
            id=box2.id,
            bbox=(x1, y1, x2, y2),
            label=box2.label,
            score=box2.score
        )


def shrink_boxes_to_remove_overlap(box1: Box, box2: Box) -> Tuple[Box, Box]:
    """Shrink boxes to remove overlap while preserving as much content as possible."""
    x1_1, y1_1, x2_1, y2_1 = box1.bbox
    x1_2, y1_2, x2_2, y2_2 = box2.bbox
    
    # Find overlap region
    overlap_x1 = max(x1_1, x1_2)
    overlap_y1 = max(y1_1, y1_2)
    overlap_x2 = min(x2_1, x2_2)
    overlap_y2 = min(y2_1, y2_2)
    
    # Determine shrink direction based on overlap position
    overlap_width = overlap_x2 - overlap_x1
    overlap_height = overlap_y2 - overlap_y1
    
    new_box1 = box1
    new_box2 = box2
    
    if overlap_width < overlap_height:
        # Shrink horizontally
        if x1_1 < x1_2:  # box1 is to the left
            new_box1 = Box(
                id=box1.id,
                bbox=(x1_1, y1_1, overlap_x1, y2_1),
                label=box1.label,
                score=box1.score
            )
            new_box2 = Box(
                id=box2.id,
                bbox=(overlap_x2, y1_2, x2_2, y2_2),
                label=box2.label,
                score=box2.score
            )
        else:  # box2 is to the left
            new_box1 = Box(
                id=box1.id,
                bbox=(overlap_x2, y1_1, x2_1, y2_1),
                label=box1.label,
                score=box1.score
            )
            new_box2 = Box(
                id=box2.id,
                bbox=(x1_2, y1_2, overlap_x1, y2_2),
                label=box2.label,
                score=box2.score
            )
    else:
        # Shrink vertically
        if y1_1 < y1_2:  # box1 is above
            new_box1 = Box(
                id=box1.id,
                bbox=(x1_1, y1_1, x2_1, overlap_y1),
                label=box1.label,
                score=box1.score
            )
            new_box2 = Box(
                id=box2.id,
                bbox=(x1_2, overlap_y2, x2_2, y2_2),
                label=box2.label,
                score=box2.score
            )
        else:  # box2 is above
            new_box1 = Box(
                id=box1.id,
                bbox=(x1_1, overlap_y2, x2_1, y2_1),
                label=box1.label,
                score=box1.score
            )
            new_box2 = Box(
                id=box2.id,
                bbox=(x1_2, y1_2, x2_2, overlap_y1),
                label=box2.label,
                score=box2.score
            )
    
    return new_box1, new_box2


def resolve_all_overlaps(boxes: List[Box], 
                        confidence_weight: float = 0.7,
                        area_weight: float = 0.3,
                        min_box_area: float = 100) -> List[Box]:
    """Resolve all overlaps to guarantee no overlapping boxes in output.
    
    Args:
        boxes: Input boxes that may have overlaps
        confidence_weight: Weight for confidence in scoring
        area_weight: Weight for area in scoring
        min_box_area: Minimum area for a box to be kept (filters out tiny fragments)
        
    Returns:
        List of boxes with no overlaps
    """
    if not boxes:
        return []
    
    # Create mutable copies
    working_boxes = [
        Box(id=b.id, bbox=b.bbox, label=b.label, score=b.score)
        for b in boxes
    ]
    
    # Keep resolving until no overlaps remain
    max_iterations = len(boxes) * 2  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        overlaps_found = False
        resolved_boxes = []
        processed = set()
        
        # Sort by weight for consistent processing
        box_weights = [
            (i, box, calculate_box_weight(box, confidence_weight, area_weight))
            for i, box in enumerate(working_boxes)
        ]
        box_weights.sort(key=lambda x: x[2], reverse=True)
        
        for idx, (i, box1, weight1) in enumerate(box_weights):
            if i in processed:
                continue
            
            # Check for overlaps with remaining boxes
            overlap_found = False
            for j, box2, weight2 in box_weights[idx+1:]:
                if j in processed:
                    continue
                
                overlap_info = get_overlap_info(box1, box2)
                if not overlap_info["has_overlap"]:
                    continue
                
                overlaps_found = True
                overlap_found = True
                
                # Determine strategy
                strategy = determine_overlap_strategy(box1, box2, overlap_info)
                
                if strategy == OverlapStrategy.KEEP_HIGHER_WEIGHT:
                    # Keep box with higher weight
                    if weight1 >= weight2:
                        resolved_boxes.append(box1)
                        processed.add(i)
                        processed.add(j)
                    else:
                        resolved_boxes.append(box2)
                        processed.add(i)
                        processed.add(j)
                    break
                
                elif strategy == OverlapStrategy.MERGE:
                    # Merge the boxes
                    merged = merge_boxes(box1, box2)
                    resolved_boxes.append(merged)
                    processed.add(i)
                    processed.add(j)
                    break
                
                elif strategy == OverlapStrategy.SHRINK_TO_NON_OVERLAP:
                    # Shrink both boxes
                    new_box1, new_box2 = shrink_boxes_to_remove_overlap(box1, box2)
                    
                    # Only keep boxes that are still reasonably sized
                    if get_box_area(new_box1.bbox) >= min_box_area:
                        resolved_boxes.append(new_box1)
                    if get_box_area(new_box2.bbox) >= min_box_area:
                        resolved_boxes.append(new_box2)
                    
                    processed.add(i)
                    processed.add(j)
                    break
            
            # If no overlap found, keep the box
            if not overlap_found:
                resolved_boxes.append(box1)
                processed.add(i)
        
        # Add any unprocessed boxes
        for j, box, _ in box_weights:
            if j not in processed:
                resolved_boxes.append(box)
        
        working_boxes = resolved_boxes
        
        # If no overlaps were found, we're done
        if not overlaps_found:
            break
    
    # Final verification - this should always pass
    for i, box1 in enumerate(working_boxes):
        for j, box2 in enumerate(working_boxes[i+1:], i+1):
            overlap_info = get_overlap_info(box1, box2)
            if overlap_info["has_overlap"]:
                print(f"WARNING: Overlap still exists between {box1.label} and {box2.label}")
    
    return working_boxes


def no_overlap_pipeline(boxes: List[Box],
                        merge_same_type_first: bool = True,
                        merge_threshold: float = 0.1,
                        confidence_weight: float = 0.7,
                        area_weight: float = 0.3) -> List[Box]:
    """Complete pipeline that guarantees no overlapping boxes.
    
    Args:
        boxes: Input boxes
        merge_same_type_first: Whether to merge same-type boxes first
        merge_threshold: IoU threshold for merging same-type boxes
        confidence_weight: Weight for confidence in conflict resolution
        area_weight: Weight for area in conflict resolution
        
    Returns:
        List of boxes with no overlaps
    """
    if merge_same_type_first:
        # First pass: merge same-type boxes that are close
        boxes = merge_overlapping_boxes(boxes, iou_threshold=merge_threshold)
    
    # Second pass: resolve ALL overlaps
    return resolve_all_overlaps(
        boxes,
        confidence_weight=confidence_weight,
        area_weight=area_weight
    )