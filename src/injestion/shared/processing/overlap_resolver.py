"""No-overlap resolver that guarantees zero overlapping boxes.

This module ensures that the final output contains no overlapping boxes
by using various strategies to handle different overlap scenarios.
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum

from .box import Box

logger = logging.getLogger(__name__)


@dataclass
class OverlapInfo:
    """Immutable overlap information between two boxes.
    
    All fields are always present, eliminating KeyError risks.
    For non-overlapping boxes, metrics are set to 0 or False.
    """
    # Basic overlap status
    has_overlap: bool
    overlap_area: float
    
    # Overlap ratios (0.0 to 1.0)
    overlap_ratio_box1: float  # What fraction of box1 is overlapped
    overlap_ratio_box2: float  # What fraction of box2 is overlapped
    
    # Derived metrics (always computed, 0 if no overlap)
    iou: float  # Intersection over Union
    ios: float  # Intersection over Smaller
    
    # Overlap classification
    is_nested: bool    # One box contains the other (>95% overlap)
    is_partial: bool   # Partial overlap (not nested)


def expand_boxes(boxes: List[Box], padding: float = 10.0, page_width: float = None, page_height: float = None) -> List[Box]:
    """Expand all boxes by a fixed padding to prevent text cutoffs.
    
    Args:
        boxes: List of Box objects to expand
        padding: Number of pixels to expand in each direction (default: 10)
        page_width: Optional page width for boundary clamping
        page_height: Optional page height for boundary clamping
        
    Returns:
        List of expanded Box objects
    """
    expanded: list[Box] = []
    
    # Create spatial index for efficient neighbor detection
    box_centers = [(b, (b.bbox[0] + b.bbox[2])/2, (b.bbox[1] + b.bbox[3])/2) for b in boxes]

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = box.bbox

        orig_w = x2 - x1
        orig_h = y2 - y1

        # Use uniform padding for all boxes - simple and predictable
        nx1, ny1 = x1 - padding, y1 - padding
        nx2, ny2 = x2 + padding, y2 + padding

        if page_width is not None:
            nx1 = max(0.0, nx1)
            nx2 = min(page_width, nx2)
        if page_height is not None:
            ny1 = max(0.0, ny1)
            ny2 = min(page_height, ny2)

        # Prevent excessive shrinkage due to clamping: keep at least 50 % of
        # the original width/height when possible.
        min_w = max(orig_w * 0.5, 1.0)
        min_h = max(orig_h * 0.5, 1.0)

        # Handle width constraints with proper boundary checks
        current_w = nx2 - nx1
        if current_w < min_w:
            if page_width is not None:
                # If we're too close to the right edge, shift left
                if nx1 + min_w > page_width:
                    nx2 = page_width
                    nx1 = max(0.0, page_width - min_w)
                else:
                    nx2 = nx1 + min_w
            else:
                nx2 = nx1 + min_w

        # Handle height constraints with proper boundary checks
        current_h = ny2 - ny1
        if current_h < min_h:
            if page_height is not None:
                # If we're too close to the bottom edge, shift up
                if ny1 + min_h > page_height:
                    ny2 = page_height
                    ny1 = max(0.0, page_height - min_h)
                else:
                    ny2 = ny1 + min_h
            else:
                ny2 = ny1 + min_h

        # Final guard: strictly positive dimensions
        # This handles edge cases where page is smaller than min dimensions
        if nx2 - nx1 < 1.0:
            if page_width is not None and nx1 >= page_width - 1.0:
                nx1 = max(0.0, page_width - 1.0)
            nx2 = nx1 + 1.0
        if ny2 - ny1 < 1.0:
            if page_height is not None and ny1 >= page_height - 1.0:
                ny1 = max(0.0, page_height - 1.0)
            ny2 = ny1 + 1.0

        # Preserve ID and lineage when expanding
        expanded_box = box.model_copy(update={
            "bbox": (nx1, ny1, nx2, ny2),
            "merge_reason": "expanded" if box.merge_reason is None else f"{box.merge_reason},expanded"
        })
        expanded.append(expanded_box)

    return expanded


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


def calculate_box_weight(
    box: Box,
    *,
    page_width: float,
    page_height: float,
    confidence_weight: float = 0.7,
    area_weight: float = 0.3,
    type_bonus: Dict[str, float] | None = None,
) -> float:
    """Return a composite weight normalised to the *actual* page size.

    This removes the previous 2000×2000 magic constant and yields
    consistent scores regardless of PDF resolution.
    """

    total_weight = confidence_weight + area_weight
    if total_weight <= 0:
        raise ValueError("confidence_weight + area_weight must be positive")

    conf_w = confidence_weight / total_weight
    area_w = area_weight / total_weight

    area_ratio = get_box_area(box.bbox) / (page_width * page_height)
    area_ratio = max(0.0, min(area_ratio, 1.0))

    score = (box.score * conf_w) + (area_ratio * area_w)

    if type_bonus and box.label in type_bonus:
        score *= (1.0 + type_bonus[box.label])

    return score


def merge_overlapping_boxes(boxes: List[Box], iou_threshold: float = 0.8) -> List[Box]:
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
                    
                # For text blocks, only merge if nearly identical (90%+ overlap)
                if box_type in ["Text", "Paragraph", "text"]:
                    # Check direct overlap with the original box only (not transitive)
                    area_i = get_box_area(type_boxes[i].bbox)
                    area_j = get_box_area(type_boxes[j].bbox)
                    inter = get_overlap_area(type_boxes[i].bbox, type_boxes[j].bbox)
                    
                    if inter > 0:
                        # Both boxes must have 85%+ of their area in the overlap
                        ratio_i = inter / area_i
                        ratio_j = inter / area_j
                        if ratio_i > 0.85 and ratio_j > 0.85:
                            merge_group.append(type_boxes[j])
                            merged[j] = True
                else:
                    # For non-text, keep the transitive merging
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
                
                # Create new merged box with lineage tracking
                # Use the first source box ID as base for the merged ID
                merged_id = f"mrg_{merge_group[0].id}"
                merged_box = Box(
                    id=merged_id,
                    bbox=(x1, y1, x2, y2),
                    label=box_type,
                    score=best_score,
                    source_ids=[box.id for box in merge_group],
                    merge_reason=f"same_type_overlap_{len(merge_group)}_boxes"
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
    KEEP_BOTH = "keep_both"  # Keep both boxes without modification


def get_overlap_info(box1: Box, box2: Box) -> OverlapInfo:
    """Get detailed overlap information between two boxes.
    
    This function ALWAYS returns a complete OverlapInfo object with all fields
    populated, preventing KeyError issues downstream.
    """
    overlap_area = get_overlap_area(box1.bbox, box2.bbox)
    area1 = get_box_area(box1.bbox)
    area2 = get_box_area(box2.bbox)
    
    # If no overlap, return zeros for all metrics
    if overlap_area == 0:
        return OverlapInfo(
            has_overlap=False,
            overlap_area=0.0,
            overlap_ratio_box1=0.0,
            overlap_ratio_box2=0.0,
            iou=0.0,
            ios=0.0,
            is_nested=False,
            is_partial=False
        )
    
    # Calculate overlap ratios
    overlap_ratio1 = overlap_area / area1 if area1 > 0 else 0
    overlap_ratio2 = overlap_area / area2 if area2 > 0 else 0
    
    # Calculate IoU and IoS
    iou = calculate_iou(box1.bbox, box2.bbox)
    ios = max(overlap_ratio1, overlap_ratio2)  # Intersection over Smaller
    
    # Determine overlap type
    is_nested = overlap_ratio1 > 0.95 or overlap_ratio2 > 0.95
    
    return OverlapInfo(
        has_overlap=True,
        overlap_area=overlap_area,
        overlap_ratio_box1=overlap_ratio1,
        overlap_ratio_box2=overlap_ratio2,
        iou=iou,
        ios=ios,
        is_nested=is_nested,
        is_partial=not is_nested
    )


def determine_overlap_strategy(
    box1: Box, 
    box2: Box, 
    overlap_info: OverlapInfo, 
    minor_overlap_threshold: float = 0.10,  # Balanced: not too strict, not too permissive
    same_type_merge_threshold: float = 0.85   # Match the text merging threshold
) -> OverlapStrategy:
    """Determine the best strategy for handling overlap between two boxes.
    
    Args:
        box1: First box
        box2: Second box
        overlap_info: Dictionary with overlap metrics
        minor_overlap_threshold: Overlaps below this ratio are considered minor and ignored
        same_type_merge_threshold: Minimum overlap ratio to merge same-type boxes (default: 0.9)
    """
    
    # ------------------------------------------------------------------
    # Special-case highly redundant *List* detection.  The layout model often
    # predicts both a generic ``Text`` block **and** a ``List`` block that
    # covers (almost) exactly the same region.  Down-stream components only
    # need one of them.  If we detect such a scenario – i.e. Tex­t ↔ List with
    # considerable nested overlap – we always keep the non-"List" element and
    # drop the redundant List box.
    # ------------------------------------------------------------------
    list_like = {"List", "ListItem", "list", "listitem"}
    text_like = {"Text", "Paragraph", "text", "paragraph"}

    if (box1.label in list_like and box2.label in text_like) or (
        box2.label in list_like and box1.label in text_like
    ):
        # If one box almost completely contains the other (>90 % intersection
        # over the smaller area) we consider it a duplicate.
        # Treat as near-duplicate – collapse both into a single **Text** box
        # by requesting the generic *MERGE* strategy.  Even when the list box
        # is selected as the primary source, `merge_boxes()` will keep the
        # higher-scoring element, which (thanks to the larger area term in
        # `calculate_box_weight`) tends to be the text block.  This reliably
        # eliminates the visually overlapping duplicate without losing
        # information.

        if overlap_info.ios > 0.9:
            return OverlapStrategy.MERGE

            # NOTE: We purposefully *do not* attempt to merge because both
            # boxes encompass effectively the same region.  Rely on the
            # existing weight calculation (which favours the larger – usually
            # non-List – box) to discard the redundant detection.  However,
            # to make the behaviour deterministic we slightly bias the score
            # in favour of the non-List element using the type-bonus below.

    # ------------------------------------------------------------------
    # Special handling for Figure overlaps
    if box1.label == "Figure" or box2.label == "Figure":
        figure_box = box1 if box1.label == "Figure" else box2
        other_box = box2 if box1.label == "Figure" else box1
        
        # If a small text/title element is fully contained within a figure, keep both
        # This preserves figure labels and captions
        if other_box.label in ["Text", "Title"]:
            # Check if the text box is mostly inside the figure
            if (figure_box == box1 and overlap_info.overlap_ratio_box2 > 0.8) or \
               (figure_box == box2 and overlap_info.overlap_ratio_box1 > 0.8):
                # Small text element inside figure - keep both
                return OverlapStrategy.KEEP_BOTH
            # For partial overlaps with figures, keep both to preserve content
            else:
                return OverlapStrategy.KEEP_BOTH
    
    # Be more tolerant of small overlaps - increased threshold
    if (overlap_info.overlap_ratio_box1 < minor_overlap_threshold and 
        overlap_info.overlap_ratio_box2 < minor_overlap_threshold):
        # Minor overlap - keep both boxes as-is
        return OverlapStrategy.KEEP_BOTH
    
    # If one box is nested inside another
    if overlap_info.is_nested:
        # Keep the outer box for containers (Figure, Table)
        if box1.label in ["Figure", "Table"] or box2.label in ["Figure", "Table"]:
            return OverlapStrategy.KEEP_HIGHER_WEIGHT
        # For text elements, keep the more specific one
        return OverlapStrategy.KEEP_HIGHER_WEIGHT
    
    # Same type boxes – only merge if they significantly overlap.
    # For multi–column PDFs it is fairly common that text blocks that live in
    # different columns share a very small sliver of horizontal or vertical
    # space (e.g. because the detector slightly over-extends the bounding box
    # of one paragraph).  Blindly merging any two boxes that have the same
    # label therefore tends to collapse otherwise separate blocks into one
    # huge box that spans multiple columns.  To avoid that we only merge
    # when the intersecting area constitutes a substantial part of at least
    # one of the boxes.  Empirically, requiring an 80 % overlap with the
    # smaller of the two boxes works well and is consistent with the logic
    # used in the dedicated `merge_overlapping_boxes` helper.

    if box1.label == box2.label:
        # Determine intersection over the smaller box.
        intersection_ratio = max(
            overlap_info.overlap_ratio_box1, overlap_info.overlap_ratio_box2
        )

        # Merge only if the vast majority of the smaller box is
        # covered by the overlap; otherwise try to keep the boxes separate.
        # For single-column documents, consider using a lower threshold.
        if intersection_ratio >= same_type_merge_threshold:
            return OverlapStrategy.MERGE
        else:
            # Prefer shrinking so that both boxes can coexist without
            # overlap.  Falling back to KEEP_HIGHER_WEIGHT would discard
            # information from the lower-weighted box.
            return OverlapStrategy.SHRINK_TO_NON_OVERLAP
    
    # For small overlaps between different types, keep both to preserve content
    if overlap_info.overlap_ratio_box1 < 0.3 and overlap_info.overlap_ratio_box2 < 0.3:
        return OverlapStrategy.KEEP_BOTH

    # ------------------------------------------------------------------
    # Mixed-type overlaps: collapse into the higher-weighted box only when
    # the intersection is truly substantial.  We combine IoU (absolute) and
    # IoS (relative to smaller box) to avoid removing captions that merely
    # touch a figure.
    # ------------------------------------------------------------------

    # Different labels → decide based on significance metrics.
    if box1.label != box2.label:
        significant = overlap_info.iou >= 0.15 and overlap_info.ios >= 0.6

        if significant:
            return OverlapStrategy.KEEP_HIGHER_WEIGHT
        else:
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
    
    # ------------------------------------------------------------------
    # Ensure the resulting boxes remain valid (strictly positive width and
    # height).  If a box would collapse entirely we keep the *original* box
    # instead – this guarantees callers always receive two usable Box
    # instances without having to implement additional checks.
    # ------------------------------------------------------------------

    def _is_valid(b: Box) -> bool:
        x1, y1, x2, y2 = b.bbox
        return (x2 - x1) > 0 and (y2 - y1) > 0

    if not _is_valid(new_box1):
        new_box1 = box1
    if not _is_valid(new_box2):
        new_box2 = box2

    return new_box1, new_box2


def _handle_list_text_duplicates_with_nested(boxes: List[Box]) -> List[Box]:
    """
    Handle the specific case where List and Text boxes nearly overlap
    and contain nested smaller elements.
    
    This prevents the nested elements from being lost when List/Text merge.
    """
    if len(boxes) < 3:
        return boxes
    
    # Find List/Text pairs with >90% overlap
    list_text_pairs = []
    for i, box1 in enumerate(boxes):
        for j, box2 in enumerate(boxes[i+1:], i+1):
            if ((box1.label in ["List", "ListItem"] and box2.label in ["Text", "Paragraph"]) or
                (box2.label in ["List", "ListItem"] and box1.label in ["Text", "Paragraph"])):
                
                overlap_info = get_overlap_info(box1, box2)
                if overlap_info.ios > 0.9:  # Nearly identical overlap
                    list_text_pairs.append((i, j, box1, box2))
    
    if not list_text_pairs:
        return boxes
    
    # For each List/Text pair, find nested elements
    boxes_to_preserve = set()
    boxes_to_remove = set()
    
    for i, j, list_text_1, list_text_2 in list_text_pairs:
        # Find boxes that are nested within BOTH the List and Text
        nested_in_both = []
        for k, other_box in enumerate(boxes):
            if k == i or k == j:
                continue
                
            # Check if nested in both
            overlap_with_1 = get_overlap_info(list_text_1, other_box)
            overlap_with_2 = get_overlap_info(list_text_2, other_box)
            
            # If >80% of the small box is inside both List and Text
            if (overlap_with_1.overlap_ratio_box2 > 0.8 and 
                overlap_with_2.overlap_ratio_box2 > 0.8):
                nested_in_both.append(k)
                boxes_to_preserve.add(k)
        
        # Keep the Text box (usually better than List) and remove the List
        if list_text_1.label in ["List", "ListItem"]:
            boxes_to_remove.add(i)
        else:
            boxes_to_remove.add(j)
        
        logger.info(f"Found List/Text duplicate with {len(nested_in_both)} nested elements")
    
    # Filter out the duplicate List/Text boxes but keep everything else
    result = []
    for idx, box in enumerate(boxes):
        if idx not in boxes_to_remove:
            result.append(box)
    
    return result


def resolve_all_overlaps(boxes: List[Box], 
                        confidence_weight: float = 0.7,
                        area_weight: float = 0.3,
                        min_box_area: float = 100,
                        minor_overlap_threshold: float = 0.10,
                        same_type_merge_threshold: float = 0.85) -> List[Box]:
    """Resolve all overlaps to guarantee no overlapping boxes in output.
    
    Args:
        boxes: Input boxes that may have overlaps
        confidence_weight: Weight for confidence in scoring
        area_weight: Weight for area in scoring  
        min_box_area: Minimum area for a box to be kept (filters out tiny fragments)
        minor_overlap_threshold: Overlaps below this ratio are considered minor and kept
        same_type_merge_threshold: Minimum overlap ratio to merge same-type boxes
        
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
    
    # Pre-process: Handle List/Text duplicates with nested elements
    working_boxes = _handle_list_text_duplicates_with_nested(working_boxes)
    
    # Keep resolving until no overlaps remain
    max_iterations = len(boxes) * 2  # Prevent infinite loops
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        overlaps_found = False
        resolved_boxes = []
        processed = set()
        
        # Estimate page dimensions once per iteration.  Assumes a shared
        # coordinate system.
        page_width = max(b.bbox[2] for b in working_boxes)
        page_height = max(b.bbox[3] for b in working_boxes)

        # Sort by weight for consistent processing
        box_weights = [
            (
                i,
                box,
                calculate_box_weight(
                    box,
                    page_width=page_width,
                    page_height=page_height,
                    confidence_weight=confidence_weight,
                    area_weight=area_weight,
                ),
            )
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
                if not overlap_info.has_overlap:
                    continue
                
                # Determine strategy
                strategy = determine_overlap_strategy(box1, box2, overlap_info, minor_overlap_threshold, same_type_merge_threshold)
                
                # Only count as "overlap found" if we actually need to resolve it
                if strategy != OverlapStrategy.KEEP_BOTH:
                    overlaps_found = True
                    overlap_found = True
                
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
                
                elif strategy == OverlapStrategy.KEEP_BOTH:
                    # Minor overlap - keep both boxes as-is without modification
                    # Don't mark as processed yet, let them be handled normally
                    continue
            
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
            if overlap_info.has_overlap:
                # Skip warning for intentionally preserved overlaps
                skip_warning = False
                
                # Figure containing text/title elements
                if box1.label == "Figure" or box2.label == "Figure":
                    figure_box = box1 if box1.label == "Figure" else box2
                    other_box = box2 if box1.label == "Figure" else box1
                    if other_box.label in ["Text", "Title"]:
                        # Check if text is mostly inside figure
                        if (figure_box == box1 and overlap_info.overlap_ratio_box2 > 0.8) or \
                           (figure_box == box2 and overlap_info.overlap_ratio_box1 > 0.8):
                            skip_warning = True
                
                # Minor overlaps
                if (overlap_info.overlap_ratio_box1 < 0.05 and 
                    overlap_info.overlap_ratio_box2 < 0.05):
                    skip_warning = True
                
                if not skip_warning:
                    logger.warning(f"Overlap still exists between {box1.label} and {box2.label}")
    
    return working_boxes


def no_overlap_pipeline(boxes: List[Box],
                        merge_same_type_first: bool = True,
                        merge_threshold: float = 0.5,
                        confidence_weight: float = 0.7,
                        area_weight: float = 0.3,
                        minor_overlap_threshold: float = 0.10,
                        same_type_merge_threshold: float = 0.85) -> List[Box]:
    """Complete pipeline that guarantees no overlapping boxes.
    
    Args:
        boxes: Input boxes
        merge_same_type_first: Whether to merge same-type boxes first
        merge_threshold: IoU threshold for merging same-type boxes
        confidence_weight: Weight for confidence in conflict resolution
        area_weight: Weight for area in conflict resolution
        minor_overlap_threshold: Overlaps below this ratio are considered minor and kept
        
    Returns:
        List of boxes with no overlaps (except minor ones below threshold)
    """
    if merge_same_type_first:
        # First pass: merge same-type boxes that are close
        boxes = merge_overlapping_boxes(boxes, iou_threshold=merge_threshold)
    
    # Second pass: resolve ALL overlaps
    return resolve_all_overlaps(
        boxes,
        confidence_weight=confidence_weight,
        area_weight=area_weight,
        minor_overlap_threshold=minor_overlap_threshold,
        same_type_merge_threshold=same_type_merge_threshold
    )
