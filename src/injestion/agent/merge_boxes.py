"""Simple geometric merging of overlapping bounding boxes.

This module provides functionality to merge overlapping boxes of the same type
without using LLM refinement. It's a purely geometric approach based on
intersection over union (IoU) or simple overlap detection.
"""

from __future__ import annotations

import uuid
from typing import List, Tuple, Set
from dataclasses import dataclass

from .refine_layout import Box


def calculate_iou(box1: Tuple[float, float, float, float], 
                  box2: Tuple[float, float, float, float]) -> float:
    """Calculate Intersection over Union between two boxes.
    
    Args:
        box1: (x1, y1, x2, y2) coordinates
        box2: (x1, y1, x2, y2) coordinates
        
    Returns:
        IoU score between 0 and 1
    """
    x1_inter = max(box1[0], box2[0])
    y1_inter = max(box1[1], box2[1])
    x2_inter = min(box1[2], box2[2])
    y2_inter = min(box1[3], box2[3])
    
    # Check if boxes actually intersect
    if x2_inter < x1_inter or y2_inter < y1_inter:
        return 0.0
    
    # Calculate intersection area
    inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
    
    # Calculate union area
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = box1_area + box2_area - inter_area
    
    # Avoid division by zero
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area


def boxes_overlap(box1: Tuple[float, float, float, float], 
                  box2: Tuple[float, float, float, float],
                  min_overlap: float = 0.1) -> bool:
    """Check if two boxes overlap significantly.
    
    Args:
        box1: (x1, y1, x2, y2) coordinates
        box2: (x1, y1, x2, y2) coordinates
        min_overlap: Minimum IoU to consider boxes as overlapping
        
    Returns:
        True if boxes overlap more than min_overlap
    """
    return calculate_iou(box1, box2) > min_overlap


def merge_two_boxes(box1: Tuple[float, float, float, float], 
                    box2: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Merge two boxes by taking the bounding box that contains both.
    
    Args:
        box1: (x1, y1, x2, y2) coordinates
        box2: (x1, y1, x2, y2) coordinates
        
    Returns:
        Merged bounding box coordinates
    """
    x1 = min(box1[0], box2[0])
    y1 = min(box1[1], box2[1])
    x2 = max(box1[2], box2[2])
    y2 = max(box1[3], box2[3])
    
    return (x1, y1, x2, y2)


def merge_overlapping_boxes(boxes: List[Box], 
                           iou_threshold: float = 0.1,
                           same_type_only: bool = True) -> List[Box]:
    """Merge overlapping boxes of the same type.
    
    This function uses a greedy approach to merge boxes that overlap
    significantly and have the same label (type).
    
    Args:
        boxes: List of Box objects to merge
        iou_threshold: Minimum IoU to consider boxes for merging
        same_type_only: If True, only merge boxes with the same label
        
    Returns:
        List of merged boxes
    """
    if not boxes:
        return []
    
    # Create a list of boxes with their merge status
    box_data = [(i, box, False) for i, box in enumerate(boxes)]  # (index, box, is_merged)
    merged_boxes = []
    
    # Process each box
    for i, (idx1, box1, merged1) in enumerate(box_data):
        if merged1:
            continue
            
        # Start a new merged box with box1
        current_bbox = box1.bbox
        current_label = box1.label
        current_score = box1.score
        merged_indices = {idx1}
        
        # Try to merge with subsequent boxes
        changed = True
        while changed:
            changed = False
            for j, (idx2, box2, merged2) in enumerate(box_data):
                if idx2 in merged_indices or merged2:
                    continue
                    
                # Check if we should merge
                should_merge = True
                if same_type_only and box1.label != box2.label:
                    should_merge = False
                elif not boxes_overlap(current_bbox, box2.bbox, iou_threshold):
                    should_merge = False
                    
                if should_merge:
                    # Merge the boxes
                    current_bbox = merge_two_boxes(current_bbox, box2.bbox)
                    current_score = max(current_score, box2.score)  # Take higher confidence
                    merged_indices.add(idx2)
                    changed = True
        
        # Mark all merged boxes
        for idx in merged_indices:
            for k, (box_idx, _, _) in enumerate(box_data):
                if box_idx == idx:
                    box_data[k] = (box_idx, box_data[k][1], True)
        
        # Create the merged box
        merged_box = Box(
            id=str(uuid.uuid4())[:8],
            bbox=current_bbox,
            label=current_label,
            score=current_score
        )
        merged_boxes.append(merged_box)
    
    return merged_boxes


def merge_boxes_simple(boxes: List[Box], 
                      overlap_threshold: float = 0.5) -> List[Box]:
    """Simpler merging based on significant overlap (>50% by default).
    
    This is a more aggressive merging strategy that merges boxes if either box
    overlaps the other by more than the threshold percentage.
    
    Args:
        boxes: List of Box objects to merge
        overlap_threshold: Fraction of smaller box that must overlap to merge
        
    Returns:
        List of merged boxes
    """
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
    for label, type_boxes in boxes_by_type.items():
        # Sort by area (larger boxes first)
        type_boxes.sort(key=lambda b: (b.bbox[2] - b.bbox[0]) * (b.bbox[3] - b.bbox[1]), reverse=True)
        
        used = set()
        
        for i, box1 in enumerate(type_boxes):
            if i in used:
                continue
                
            # Start with this box
            merged_bbox = box1.bbox
            merged_score = box1.score
            group = {i}
            
            # Find all boxes that overlap significantly
            for j, box2 in enumerate(type_boxes):
                if j <= i or j in used:
                    continue
                    
                # Calculate overlap relative to smaller box
                x1_inter = max(merged_bbox[0], box2.bbox[0])
                y1_inter = max(merged_bbox[1], box2.bbox[1])
                x2_inter = min(merged_bbox[2], box2.bbox[2])
                y2_inter = min(merged_bbox[3], box2.bbox[3])
                
                if x2_inter > x1_inter and y2_inter > y1_inter:
                    inter_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
                    box2_area = (box2.bbox[2] - box2.bbox[0]) * (box2.bbox[3] - box2.bbox[1])
                    
                    # If significant overlap with smaller box
                    if box2_area > 0 and inter_area / box2_area > overlap_threshold:
                        merged_bbox = merge_two_boxes(merged_bbox, box2.bbox)
                        merged_score = max(merged_score, box2.score)
                        group.add(j)
            
            # Mark all boxes in group as used
            used.update(group)
            
            # Create merged box
            merged_box = Box(
                id=str(uuid.uuid4())[:8],
                bbox=merged_bbox,
                label=label,
                score=merged_score
            )
            merged_boxes.append(merged_box)
    
    return merged_boxes