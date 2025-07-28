"""Weighted conflict resolution based on confidence and area.

This module provides a more nuanced approach to resolving conflicts that
considers both the confidence score and the area of boxes, rather than
just relying on type hierarchy.
"""

from __future__ import annotations

import uuid
from typing import List, Tuple, Dict
from dataclasses import dataclass

from .refine_layout import Box
from .merge_boxes import calculate_iou
from .merge_boxes_advanced import get_overlap_area, get_box_area


def calculate_box_weight(box: Box, 
                        confidence_weight: float = 0.7,
                        area_weight: float = 0.3,
                        type_bonus: Dict[str, float] = None) -> float:
    """Calculate a weight score for a box based on multiple factors.
    
    Args:
        box: The box to score
        confidence_weight: Weight given to confidence score (0-1)
        area_weight: Weight given to box area (0-1)
        type_bonus: Optional bonus scores for specific types
        
    Returns:
        Weight score for the box
    """
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


def resolve_conflicts_weighted(boxes: List[Box],
                             confidence_weight: float = 0.7,
                             area_weight: float = 0.3,
                             overlap_threshold: float = 0.7,
                             type_adjustments: Dict[str, float] = None) -> List[Box]:
    """Resolve conflicts using weighted scoring.
    
    Args:
        boxes: List of boxes with potential conflicts
        confidence_weight: How much to weight confidence scores
        area_weight: How much to weight box area
        overlap_threshold: Minimum overlap to consider a conflict
        type_adjustments: Optional adjustments for specific types
            e.g., {"List": -0.2} to penalize List boxes
        
    Returns:
        List of boxes with conflicts resolved
    """
    if type_adjustments is None:
        type_adjustments = {}
    
    # Calculate weight for each box
    box_weights = [
        (i, box, calculate_box_weight(box, confidence_weight, area_weight, type_adjustments))
        for i, box in enumerate(boxes)
    ]
    
    # Sort by weight (highest first)
    box_weights.sort(key=lambda x: x[2], reverse=True)
    
    resolved_boxes = []
    processed = set()
    
    for idx, (i, box1, weight1) in enumerate(box_weights):
        if i in processed:
            continue
        
        # Find conflicts
        conflicts = []
        for j, box2, weight2 in box_weights[idx+1:]:
            if j in processed:
                continue
                
            # Check for significant overlap between different types
            if box1.label != box2.label:
                overlap_area = get_overlap_area(box1.bbox, box2.bbox)
                box2_area = get_box_area(box2.bbox)
                
                if box2_area > 0 and overlap_area / box2_area > overlap_threshold:
                    conflicts.append((j, weight2))
        
        # Keep the current box
        resolved_boxes.append(box1)
        processed.add(i)
        
        # Process conflicts based on weight difference
        for j, weight2 in conflicts:
            # If the weight difference is small, we might want to keep both
            # by adjusting boundaries (future enhancement)
            weight_ratio = weight2 / weight1 if weight1 > 0 else 0
            
            if weight_ratio < 0.8:  # Significantly lower weight
                processed.add(j)  # Remove the conflicting box
            else:
                # Weights are close - this might be a case where we should
                # investigate further or try to split
                # For now, still remove but log it
                processed.add(j)
                print(f"Close weight conflict: {box1.label} ({weight1:.3f}) vs box {j} ({weight2:.3f})")
    
    return resolved_boxes


def smart_merge_and_resolve(boxes: List[Box],
                          merge_same_type: bool = True,
                          merge_threshold: float = 0.1,
                          confidence_weight: float = 0.7,
                          area_weight: float = 0.3) -> List[Box]:
    """Smart merging with weighted conflict resolution.
    
    This function merges same-type boxes and resolves conflicts between
    different types using weighted scoring.
    
    Args:
        boxes: Input boxes
        merge_same_type: Whether to merge same-type boxes first
        merge_threshold: IoU threshold for merging
        confidence_weight: Weight for confidence in conflict resolution
        area_weight: Weight for area in conflict resolution
        
    Returns:
        Processed boxes
    """
    # First, merge same-type boxes if requested
    if merge_same_type:
        from .merge_boxes import merge_overlapping_boxes
        boxes = merge_overlapping_boxes(boxes, iou_threshold=merge_threshold)
    
    # Resolve conflicts with weighted approach
    return resolve_conflicts_weighted(
        boxes,
        confidence_weight=confidence_weight,
        area_weight=area_weight
    )


def analyze_conflict_weights(boxes: List[Box]) -> List[Dict]:
    """Analyze potential conflicts and their weights for debugging."""
    results = []
    
    for i, box1 in enumerate(boxes):
        weight1 = calculate_box_weight(box1)
        
        for j, box2 in enumerate(boxes):
            if i >= j or box1.label == box2.label:
                continue
                
            overlap_area = get_overlap_area(box1.bbox, box2.bbox)
            if overlap_area > 0:
                weight2 = calculate_box_weight(box2)
                box1_area = get_box_area(box1.bbox)
                box2_area = get_box_area(box2.bbox)
                
                results.append({
                    'box1': {
                        'id': box1.id,
                        'label': box1.label,
                        'score': box1.score,
                        'area': box1_area,
                        'weight': weight1
                    },
                    'box2': {
                        'id': box2.id,
                        'label': box2.label,
                        'score': box2.score,
                        'area': box2_area,
                        'weight': weight2
                    },
                    'overlap_area': overlap_area,
                    'overlap_pct': overlap_area / min(box1_area, box2_area),
                    'weight_ratio': weight2 / weight1 if weight1 > 0 else 0,
                    'winner': box1.label if weight1 > weight2 else box2.label
                })
    
    return sorted(results, key=lambda x: x['overlap_area'], reverse=True)