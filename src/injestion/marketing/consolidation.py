"""Fixed box consolidation operations for marketing documents."""

from typing import List, Tuple, Optional
from ..processing.box import Box


class BoxConsolidator:
    """Handles box merging, overlap resolution, and expansion for marketing layouts."""
    
    def __init__(
        self,
        merge_threshold: float = 0.2,
        expand_padding: float = 10.0
    ):
        """Initialize box consolidator.
        
        Parameters
        ----------
        merge_threshold : float
            IoU threshold for merging same-type boxes (0.2 = 20% overlap)
        expand_padding : float
            Pixels to expand boxes in each direction
        """
        self.merge_threshold = merge_threshold
        self.expand_padding = expand_padding
    
    def consolidate_boxes(
        self, 
        boxes: List[Box], 
        image_width: Optional[float] = None,
        image_height: Optional[float] = None
    ) -> List[Box]:
        """Apply full consolidation pipeline to boxes.
        
        Steps:
        1. Filter out suspiciously narrow text boxes
        2. Remove overlapping boxes of different types
        3. Merge overlapping boxes of same type
        4. Safely expand boxes if configured
        
        Parameters
        ----------
        boxes : List[Box]
            Input boxes to consolidate
        image_width : float, optional
            Page width for boundary constraints
        image_height : float, optional
            Page height for boundary constraints
            
        Returns
        -------
        List[Box]
            Consolidated boxes
        """
        if not boxes:
            return boxes
            
        # Filter out narrow text boxes that are likely detection errors
        boxes = self._filter_narrow_text_boxes(boxes)
        
        # Remove overlapping boxes of different types
        boxes = self._remove_overlapping_different_types(boxes)
        
        # Merge overlapping boxes of same type
        boxes = self._merge_overlapping_same_type(boxes)
        
        # Safely expand boxes if padding is configured
        if self.expand_padding > 0 and image_width and image_height:
            boxes = self._expand_boxes_safely(boxes, image_width, image_height)
            
        return boxes
    
    def _filter_narrow_text_boxes(self, boxes: List[Box]) -> List[Box]:
        """Filter out suspiciously narrow text boxes that likely contain garbled text.
        
        Text boxes narrower than 400px are often detection errors that capture
        only vertical slices of text, resulting in garbled output.
        """
        filtered = []
        removed_count = 0
        
        for box in boxes:
            width = box.bbox[2] - box.bbox[0]
            
            # Keep non-text boxes regardless of width
            if box.label != 'TextRegion':
                filtered.append(box)
                continue
                
            # Filter out narrow text boxes
            if width < 400:
                removed_count += 1
                print(f"  Filtering out narrow TextRegion (width={width:.0f}px, score={box.score:.2f})")
            else:
                filtered.append(box)
        
        if removed_count > 0:
            print(f"  Removed {removed_count} narrow text boxes")
            
        return filtered
    
    def _remove_overlapping_different_types(self, boxes: List[Box]) -> List[Box]:
        """Remove overlapping boxes of different types, keeping higher confidence."""
        if not boxes:
            return boxes
        
        # Sort by confidence score descending
        sorted_boxes = sorted(boxes, key=lambda b: b.score, reverse=True)
        kept_boxes = []
        
        for box in sorted_boxes:
            should_keep = True
            
            # Check against all higher confidence boxes we've kept
            for kept_box in kept_boxes:
                # If different type and significant overlap, skip this box
                if (kept_box.label != box.label and 
                    self._boxes_overlap(box.bbox, kept_box.bbox, threshold=0.5)):
                    print(f"  Removing {box.label} (score={box.score:.2f}) overlapping with {kept_box.label} (score={kept_box.score:.2f})")
                    should_keep = False
                    break
            
            if should_keep:
                kept_boxes.append(box)
        
        return kept_boxes
    
    def _merge_overlapping_same_type(self, boxes: List[Box]) -> List[Box]:
        """Merge overlapping boxes of the same type."""
        if not boxes:
            return boxes
            
        # Sort boxes by y-coordinate then x-coordinate for consistent processing
        sorted_boxes = sorted(boxes, key=lambda b: (b.bbox[1], b.bbox[0]))
        
        merged = []
        i = 0
        
        while i < len(sorted_boxes):
            current = sorted_boxes[i]
            current_bbox = list(current.bbox)
            
            # Find all boxes that overlap with current AND have same type
            j = i + 1
            boxes_to_merge = [current]
            
            while j < len(sorted_boxes):
                candidate = sorted_boxes[j]
                
                # Only merge if same type AND overlapping
                if (candidate.label == current.label and 
                    self._boxes_overlap(current_bbox, candidate.bbox, self.merge_threshold)):
                    # Expand current bbox to include candidate
                    current_bbox[0] = min(current_bbox[0], candidate.bbox[0])
                    current_bbox[1] = min(current_bbox[1], candidate.bbox[1])
                    current_bbox[2] = max(current_bbox[2], candidate.bbox[2])
                    current_bbox[3] = max(current_bbox[3], candidate.bbox[3])
                    boxes_to_merge.append(candidate)
                    sorted_boxes.pop(j)
                else:
                    j += 1
            
            # Create merged box with combined bbox
            if len(boxes_to_merge) > 1:
                # Use the highest scoring box's properties
                best_box = max(boxes_to_merge, key=lambda b: b.score)
                merged_box = Box(
                    id=best_box.id,
                    bbox=tuple(current_bbox),
                    label=best_box.label,
                    score=best_box.score
                )
                merged.append(merged_box)
                print(f"  Merged {len(boxes_to_merge)} {best_box.label} boxes")
            else:
                merged.append(current)
            
            i += 1
        
        return merged
    
    def _expand_boxes_safely(self, boxes: List[Box], page_width: float, page_height: float) -> List[Box]:
        """Expand boxes while preventing worsening of overlaps."""
        if not boxes:
            return boxes
        
        # First, calculate which boxes overlap with which
        overlaps = {}  # box_id -> set of box_ids it overlaps with
        for i, box1 in enumerate(boxes):
            overlaps[box1.id] = set()
            for j, box2 in enumerate(boxes):
                if i != j and self._boxes_overlap(box1.bbox, box2.bbox, threshold=0.0):
                    overlaps[box1.id].add(box2.id)
        
        # Now expand each box
        expanded_boxes = []
        
        for box in boxes:
            x1, y1, x2, y2 = box.bbox
            
            # Start with desired expansion
            new_x1 = x1 - self.expand_padding
            new_y1 = y1 - self.expand_padding
            new_x2 = x2 + self.expand_padding
            new_y2 = y2 + self.expand_padding
            
            # Clamp to page boundaries
            new_x1 = max(0, new_x1)
            new_x2 = min(page_width, new_x2)
            new_y1 = max(0, new_y1)
            new_y2 = min(page_height, new_y2)
            
            # For each box that this box originally overlaps with,
            # don't expand towards it
            for other_id in overlaps[box.id]:
                other_box = next(b for b in boxes if b.id == other_id)
                other_x1, other_y1, other_x2, other_y2 = other_box.bbox
                
                # Determine relative position and constrain expansion
                if x1 < other_x1 and x2 > other_x1:  # This box is to the left but overlaps
                    new_x2 = min(new_x2, x2)  # Don't expand right edge
                if x1 < other_x2 and x2 > other_x2:  # This box is to the right but overlaps
                    new_x1 = max(new_x1, x1)  # Don't expand left edge
                if y1 < other_y1 and y2 > other_y1:  # This box is above but overlaps
                    new_y2 = min(new_y2, y2)  # Don't expand bottom edge
                if y1 < other_y2 and y2 > other_y2:  # This box is below but overlaps
                    new_y1 = max(new_y1, y1)  # Don't expand top edge
            
            # For boxes we don't originally overlap with, maintain a gap
            for other_box in boxes:
                if other_box.id == box.id or other_box.id in overlaps[box.id]:
                    continue
                    
                other_x1, other_y1, other_x2, other_y2 = other_box.bbox
                gap = 2.0
                
                # Check if expansion would create new overlap
                if new_x2 > other_x1 and new_x1 < other_x2 and new_y2 > other_y1 and new_y1 < other_y2:
                    # Would create overlap - constrain expansion
                    if x2 <= other_x1:  # Originally to the left
                        new_x2 = min(new_x2, other_x1 - gap)
                    if x1 >= other_x2:  # Originally to the right
                        new_x1 = max(new_x1, other_x2 + gap)
                    if y2 <= other_y1:  # Originally above
                        new_y2 = min(new_y2, other_y1 - gap)
                    if y1 >= other_y2:  # Originally below
                        new_y1 = max(new_y1, other_y2 + gap)
            
            # Create expanded box
            expanded_box = Box(
                id=box.id,
                bbox=(new_x1, new_y1, new_x2, new_y2),
                label=box.label,
                score=box.score
            )
            expanded_boxes.append(expanded_box)
        
        print(f"  Safely expanded {len(expanded_boxes)} boxes by up to {self.expand_padding}px")
        return expanded_boxes
    
    def _boxes_overlap(self, bbox1: Tuple[float, float, float, float], 
                       bbox2: Tuple[float, float, float, float], 
                       threshold: float = 0.1) -> bool:
        """Check if two boxes overlap by at least threshold amount."""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 < x1 or y2 < y1:
            return False
            
        intersection_area = (x2 - x1) * (y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        # Check if intersection is at least threshold of smaller box
        min_area = min(area1, area2)
        return intersection_area >= (min_area * threshold)