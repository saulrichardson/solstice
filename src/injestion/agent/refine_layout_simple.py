"""Simple geometric refinement of layout boxes without LLM.

This module provides a non-LLM alternative to refine_layout.py that focuses
on merging overlapping boxes of the same type using geometric rules.
"""

from __future__ import annotations

import logging
from typing import List, Sequence

from PIL import Image

from .refine_layout import Box, RefinedPage
from .merge_boxes import merge_overlapping_boxes, merge_boxes_simple
from .merge_boxes_advanced import merge_and_resolve_conflicts, analyze_cross_type_overlaps
from .merge_boxes_weighted import smart_merge_and_resolve, analyze_conflict_weights

logger = logging.getLogger(__name__)


def refine_page_layout_simple(
    page_index: int,
    raw_boxes: Sequence[Box],
    *,
    page_image: Image.Image = None,  # Not used in simple refinement
    merge_strategy: str = "iou",
    iou_threshold: float = 0.1,
    overlap_threshold: float = 0.5,
    resolve_conflicts: bool = True,
    conflict_resolution: str = "weighted",
) -> RefinedPage:
    """Refine layout using simple geometric merging rules.
    
    This is a non-LLM alternative that merges overlapping boxes of the same type.
    
    Args:
        page_index: Page number (0-based)
        raw_boxes: List of detected boxes
        page_image: Not used in simple refinement (kept for API compatibility)
        merge_strategy: "iou" for IoU-based merging, "simple" for overlap-based
        iou_threshold: Minimum IoU for merging (used with "iou" strategy)
        overlap_threshold: Minimum overlap fraction (used with "simple" strategy)
        resolve_conflicts: Whether to resolve cross-type overlaps after merging
        conflict_resolution: Strategy for resolving conflicts ("priority", "larger", "confident", "split")
        
    Returns:
        RefinedPage with merged boxes and basic reading order
    """
    
    logger.debug(f"Simple refinement for page {page_index} with {len(raw_boxes)} boxes")
    
    # Convert to list if needed
    boxes_list = list(raw_boxes)
    
    # If conflict resolution is enabled, use the advanced pipeline
    if resolve_conflicts:
        if conflict_resolution == "weighted":
            # Use the new weighted approach
            merged_boxes = smart_merge_and_resolve(
                boxes_list,
                merge_same_type=True,
                merge_threshold=iou_threshold if merge_strategy == "iou" else 0.1,
                confidence_weight=0.7,
                area_weight=0.3
            )
        else:
            # Use the original priority-based approach
            merged_boxes = merge_and_resolve_conflicts(
                boxes_list,
                merge_same_type=True,
                iou_threshold=iou_threshold if merge_strategy == "iou" else 0.1,
                resolution_strategy=conflict_resolution
            )
        
        # Analyze what happened
        original_overlaps = analyze_cross_type_overlaps(boxes_list)
        final_overlaps = analyze_cross_type_overlaps(merged_boxes)
        
        logger.debug(f"Cross-type overlaps: {len(original_overlaps)} → {len(final_overlaps)}")
    else:
        # Apply merging based on strategy
        if merge_strategy == "iou":
            merged_boxes = merge_overlapping_boxes(
                boxes_list, 
                iou_threshold=iou_threshold,
                same_type_only=True
            )
        else:  # "simple" strategy
            merged_boxes = merge_boxes_simple(
                boxes_list,
                overlap_threshold=overlap_threshold
            )
    
    logger.debug(f"Merged {len(raw_boxes)} boxes into {len(merged_boxes)} boxes")
    
    # Generate simple reading order (top to bottom, left to right)
    reading_order = generate_reading_order(merged_boxes)
    
    return RefinedPage(
        boxes=merged_boxes,
        reading_order=reading_order,
        page_index=page_index,
        detection_dpi=200  # Default, should match detection
    )


def generate_reading_order(boxes: List[Box]) -> List[str]:
    """Generate reading order based on geometric position.
    
    Simple strategy: Sort by vertical position (top to bottom),
    then by horizontal position (left to right) for boxes at similar heights.
    
    Args:
        boxes: List of boxes to order
        
    Returns:
        List of box IDs in reading order
    """
    if not boxes:
        return []
    
    # Create list of (box, center_y, center_x) for sorting
    box_positions = []
    for box in boxes:
        center_x = (box.bbox[0] + box.bbox[2]) / 2
        center_y = (box.bbox[1] + box.bbox[3]) / 2
        box_positions.append((box, center_y, center_x))
    
    # Sort primarily by Y (with some tolerance), then by X
    # Boxes within 20 pixels vertically are considered same "line"
    line_threshold = 20
    
    def sort_key(item):
        box, y, x = item
        # Round y to nearest line_threshold to group nearby boxes
        y_group = round(y / line_threshold) * line_threshold
        return (y_group, x)
    
    box_positions.sort(key=sort_key)
    
    # Extract IDs in order
    return [box.id for box, _, _ in box_positions]


def refine_page_layout_hybrid(
    page_index: int,
    raw_boxes: Sequence[Box],
    *,
    page_image: Image.Image = None,
    pre_merge: bool = True,
    merge_strategy: str = "simple",
    use_llm: bool = False,
    **kwargs
) -> RefinedPage:
    """Hybrid approach: geometric merging followed by optional LLM refinement.
    
    This allows you to first apply simple merging rules, then optionally
    use LLM for more sophisticated refinement.
    
    Args:
        page_index: Page number (0-based)
        raw_boxes: List of detected boxes
        page_image: Page image (required if use_llm=True)
        pre_merge: Whether to apply geometric merging first
        merge_strategy: Strategy for geometric merging
        use_llm: Whether to apply LLM refinement after merging
        **kwargs: Additional arguments for merge strategies
        
    Returns:
        RefinedPage with processed boxes
    """
    
    boxes = list(raw_boxes)
    
    # Step 1: Apply geometric merging if requested
    if pre_merge:
        logger.debug("Applying geometric pre-merging...")
        refined = refine_page_layout_simple(
            page_index=page_index,
            raw_boxes=boxes,
            merge_strategy=merge_strategy,
            **kwargs
        )
        boxes = refined.boxes
    
    # Step 2: Apply LLM refinement if requested
    if use_llm:
        if page_image is None:
            raise ValueError("page_image required for LLM refinement")
            
        logger.debug("Applying LLM refinement...")
        # Import here to avoid circular dependency
        from .refine_layout import refine_page_layout
        return refine_page_layout(
            page_index=page_index,
            raw_boxes=boxes,
            page_image=page_image
        )
    
    # Return the geometrically refined result
    return RefinedPage(
        boxes=boxes,
        reading_order=generate_reading_order(boxes),
        page_index=page_index,
        detection_dpi=200
    )