"""Marketing-specific reading order detection."""

from typing import List, Tuple, Dict
import numpy as np
from ..processing.box import Box


def determine_marketing_reading_order(boxes: List[Box], page_width: float = 1600, page_height: float = 3000) -> List[str]:
    """
    Marketing-specific reading order using advanced clustering for feature boxes.
    
    This algorithm:
    1. Identifies the title/header (topmost wide box)
    2. Uses spatial clustering to group related content into feature boxes
    3. Orders clusters in a grid pattern (left-to-right, top-to-bottom)
    4. Reads all content within each cluster before moving to next
    5. Handles footer/disclaimer text at bottom
    
    Args:
        boxes: All boxes on the page
        page_width: Width of the page
        page_height: Height of the page (estimated from boxes if not provided)
        
    Returns:
        List of box IDs in reading order
    """
    if not boxes:
        return []
    
    # Estimate page height from boxes if needed
    if page_height == 3000 and boxes:
        page_height = max(box.bbox[3] for box in boxes)
    
    # Step 1: Identify header (title) - usually the widest box at the top
    header_boxes = []
    main_boxes = []
    footer_boxes = []
    
    # Find the widest box in the top 20% of the page - likely the title
    top_threshold = page_height * 0.20
    bottom_threshold = page_height * 0.80
    
    for box in boxes:
        box_center_y = (box.bbox[1] + box.bbox[3]) / 2
        box_width = box.bbox[2] - box.bbox[0]
        
        # Wide boxes at the top are likely headers/titles
        if box_center_y < top_threshold and box_width > page_width * 0.6:
            header_boxes.append(box)
        elif box_center_y > bottom_threshold:
            footer_boxes.append(box)
        else:
            main_boxes.append(box)
    
    # If no wide header found, check for any text in top area
    if not header_boxes:
        for box in boxes:
            if box.bbox[1] < top_threshold:
                header_boxes.append(box)
            elif box.bbox[1] < bottom_threshold:
                main_boxes.append(box)
            else:
                footer_boxes.append(box)
    
    # Remove header boxes from main boxes
    header_ids = set(box.id for box in header_boxes)
    main_boxes = [box for box in main_boxes if box.id not in header_ids]
    
    # Step 2: Cluster main content boxes
    clusters = _cluster_marketing_boxes(main_boxes)
    
    # Debug: Print cluster information
    print(f"\nClustering result: Found {len(clusters)} clusters from {len(main_boxes)} main boxes")
    for i, cluster in enumerate(clusters):
        # Get cluster bounds
        if cluster:
            min_x = min(b.bbox[0] for b in cluster)
            max_x = max(b.bbox[2] for b in cluster)
            min_y = min(b.bbox[1] for b in cluster)
            max_y = max(b.bbox[3] for b in cluster)
            print(f"  Cluster {i+1}: {len(cluster)} boxes, bounds: ({min_x:.0f},{min_y:.0f}) to ({max_x:.0f},{max_y:.0f})")
            for j, box in enumerate(cluster[:3]):  # Show first 3 boxes
                text_preview = box.text[:30] + '...' if hasattr(box, 'text') and box.text else 'NO TEXT'
                print(f"    Box {j+1} - {box.label}: {text_preview}")
    
    # Step 3: Order clusters in grid pattern
    ordered_clusters = _order_clusters_grid_pattern(clusters)
    
    # Step 4: Build final reading order
    reading_order = []
    
    # Add header boxes first (sorted by width desc, then position)
    if header_boxes:
        header_boxes.sort(key=lambda b: (-(b.bbox[2] - b.bbox[0]), b.bbox[1], b.bbox[0]))
        reading_order.extend([box.id for box in header_boxes])
    
    # Add clustered main content
    for cluster in ordered_clusters:
        # Within each cluster, read top-to-bottom, left-to-right
        cluster.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        reading_order.extend([box.id for box in cluster])
    
    # Add footer boxes last
    if footer_boxes:
        footer_boxes.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        reading_order.extend([box.id for box in footer_boxes])
    
    return reading_order


def _cluster_marketing_boxes(boxes: List[Box]) -> List[List[Box]]:
    """Cluster boxes that belong to the same feature/content group.
    
    Uses spatial proximity to group related boxes together.
    Marketing slides typically have distinct feature boxes that should be read as units.
    """
    if not boxes:
        return []
    
    # Debug: show all boxes
    print("\nDEBUG: Main content boxes before clustering:")
    for box in boxes[:10]:  # Show first 10
        text_preview = box.text[:30] + '...' if hasattr(box, 'text') and box.text else 'NO TEXT'
        print(f"  {box.label} @ ({box.bbox[0]:.0f},{box.bbox[1]:.0f}): {text_preview}")
    
    # Use more aggressive clustering for marketing documents
    # Group boxes that are part of the same visual feature box
    clusters = []
    unassigned = list(boxes)
    
    while unassigned:
        # Start new cluster with an unassigned box
        seed = unassigned.pop(0)
        cluster = [seed]
        
        # Keep expanding cluster until no more boxes can be added
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(unassigned):
                box = unassigned[i]
                
                # Check if this box should join the cluster
                should_join = False
                
                for cluster_box in cluster:
                    # Calculate spatial relationship
                    # Get bounding box of cluster so far
                    cluster_min_x = min(b.bbox[0] for b in cluster)
                    cluster_max_x = max(b.bbox[2] for b in cluster)
                    cluster_min_y = min(b.bbox[1] for b in cluster)
                    cluster_max_y = max(b.bbox[3] for b in cluster)
                    
                    # Check if box is within or near the cluster bounds
                    x_near = (box.bbox[0] >= cluster_min_x - 50 and box.bbox[2] <= cluster_max_x + 50)
                    y_near = (box.bbox[1] >= cluster_min_y - 50 and box.bbox[3] <= cluster_max_y + 100)
                    
                    # Also check direct proximity to any box in cluster
                    x_overlap = min(cluster_box.bbox[2], box.bbox[2]) - max(cluster_box.bbox[0], box.bbox[0])
                    y_gap = max(0, box.bbox[1] - cluster_box.bbox[3])  # Gap between bottom of cluster box and top of new box
                    
                    # Join if:
                    # 1. Box is within cluster bounds
                    # 2. OR box has significant x-overlap and small y-gap with a cluster member
                    if (x_near and y_near) or (x_overlap > 100 and y_gap < 80):
                        should_join = True
                        break
                
                if should_join:
                    cluster.append(box)
                    unassigned.pop(i)
                    changed = True
                else:
                    i += 1
        
        clusters.append(cluster)
    
    return clusters


def _order_clusters_grid_pattern(clusters: List[List[Box]]) -> List[List[Box]]:
    """Order clusters in a grid pattern (left-to-right, top-to-bottom).
    
    For marketing slides, feature boxes are typically arranged in a grid.
    This function orders the clusters to follow a natural reading pattern.
    """
    if not clusters:
        return []
    
    # Calculate center point of each cluster
    cluster_centers = []
    for cluster in clusters:
        min_x = min(box.bbox[0] for box in cluster)
        max_x = max(box.bbox[2] for box in cluster)
        min_y = min(box.bbox[1] for box in cluster)
        max_y = max(box.bbox[3] for box in cluster)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        cluster_centers.append((center_x, center_y, cluster))
    
    # Group clusters into rows based on Y position
    cluster_centers.sort(key=lambda x: x[1])  # Sort by Y
    
    rows = []
    current_row = [cluster_centers[0]]
    row_y = cluster_centers[0][1]
    
    for i in range(1, len(cluster_centers)):
        center_x, center_y, cluster = cluster_centers[i]
        
        # If Y position is close to current row, add to same row
        if abs(center_y - row_y) < 100:  # Within 100px vertically
            current_row.append(cluster_centers[i])
            # Update row Y to be average
            row_y = sum(c[1] for c in current_row) / len(current_row)
        else:
            # Start new row
            rows.append(current_row)
            current_row = [cluster_centers[i]]
            row_y = center_y
    
    if current_row:
        rows.append(current_row)
    
    # Within each row, sort by X position (left to right)
    ordered_clusters = []
    for row in rows:
        row.sort(key=lambda x: x[0])  # Sort by X
        ordered_clusters.extend([item[2] for item in row])
    
    return ordered_clusters