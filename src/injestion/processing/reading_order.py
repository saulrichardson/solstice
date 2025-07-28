"""Reading order detection with column analysis."""

from typing import List, Tuple

from ..models.box import Box


def detect_columns(boxes: List[Box], page_width: float = 1600) -> List[List[Box]]:
    """Detect column structure in the page layout."""
    if not boxes:
        return []
    
    # Get horizontal positions of text boxes (exclude wide elements like titles)
    text_boxes = [b for b in boxes if b.label in ['Text', 'List']]
    if not text_boxes:
        return [boxes]
    
    # Calculate box widths to identify potential column elements
    box_widths = [(b.bbox[2] - b.bbox[0]) for b in text_boxes]
    avg_width = sum(box_widths) / len(box_widths)
    
    # Filter out wide boxes (likely titles or spanning elements)
    column_candidates = [b for b in text_boxes if (b.bbox[2] - b.bbox[0]) < page_width * 0.6]
    
    if len(column_candidates) < 4:
        # Not enough boxes to determine columns
        return [boxes]
    
    # Analyze x-positions to find column boundaries
    x_positions = sorted([b.bbox[0] for b in column_candidates])
    
    # Look for gaps in x-positions
    gaps = []
    for i in range(1, len(x_positions)):
        gap = x_positions[i] - x_positions[i-1]
        if gap > avg_width * 0.5:  # Significant gap
            gaps.append((x_positions[i-1], x_positions[i]))
    
    if not gaps:
        # No clear column separation
        return [boxes]
    
    # For now, assume 2 columns if we found a clear gap
    if len(gaps) == 1 and gaps[0][0] < page_width * 0.6:
        # Two column layout detected
        middle = (gaps[0][0] + gaps[0][1]) / 2
        
        left_column = []
        right_column = []
        spanning_elements = []
        
        for box in boxes:
            box_center = (box.bbox[0] + box.bbox[2]) / 2
            box_width = box.bbox[2] - box.bbox[0]
            
            # Check if element spans columns
            if box_width > page_width * 0.6 or (box.bbox[0] < middle - 50 and box.bbox[2] > middle + 50):
                spanning_elements.append(box)
            elif box_center < middle:
                left_column.append(box)
            else:
                right_column.append(box)
        
        return [spanning_elements, left_column, right_column]
    
    # Default: single column
    return [boxes]


def determine_reading_order(boxes: List[Box], page_width: float = 1600) -> List[str]:
    """Determine reading order based on column layout analysis."""
    if not boxes:
        return []
    
    # Detect columns
    columns = detect_columns(boxes, page_width)
    
    reading_order = []
    
    # Process each column
    for column_boxes in columns:
        if not column_boxes:
            continue
            
        # Sort boxes in column top to bottom
        sorted_column = sorted(column_boxes, key=lambda b: b.bbox[1])
        
        # For spanning elements at the top (like titles), process them first
        if len(columns) > 1 and columns[0] == column_boxes:
            # This is the spanning elements group - sort by type priority then position
            # Prioritize titles/headers at the top
            def sort_key(box):
                type_priority = 0 if box.label in ['Title', 'Header'] else 1
                return (type_priority, box.bbox[1])  # Type first, then y-position
            
            sorted_spanning = sorted(column_boxes, key=sort_key)
            reading_order.extend([box.id for box in sorted_spanning])
        else:
            # Regular column - group nearby boxes
            column_order = []
            i = 0
            while i < len(sorted_column):
                current_y = sorted_column[i].bbox[1]
                row_boxes = [sorted_column[i]]
                
                # Collect boxes at similar y-position (same row)
                j = i + 1
                while j < len(sorted_column) and abs(sorted_column[j].bbox[1] - current_y) < 20:
                    row_boxes.append(sorted_column[j])
                    j += 1
                
                # Sort row boxes left to right
                row_boxes.sort(key=lambda b: b.bbox[0])
                column_order.extend([box.id for box in row_boxes])
                
                i = j
            
            reading_order.extend(column_order)
    
    return reading_order


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
        if box.bbox[0] < midpoint:
            left_boxes.append(box)
        else:
            right_boxes.append(box)
    
    # Sort each group by vertical position
    left_boxes.sort(key=lambda b: b.bbox[1])
    right_boxes.sort(key=lambda b: b.bbox[1])
    
    # Build reading order: left first, then right
    reading_order = []
    reading_order.extend([b.id for b in left_boxes])
    reading_order.extend([b.id for b in right_boxes])
    
    return reading_order