"""Marketing-specific reading order detection."""

from typing import List, Tuple, Dict
import numpy as np
from ..shared.processing.box import Box


def determine_marketing_reading_order(boxes: List[Box], page_width: float, page_height: float) -> List[str]:
    """
    Marketing-specific reading order using feature-aware clustering.
    
    This algorithm is specifically designed for marketing slides with:
    - A title header at the top
    - Feature boxes arranged in columns
    - Icons/figures associated with text blocks
    - Footer information at the bottom
    
    Args:
        boxes: All boxes on the page
        page_width: Width of the page
        page_height: Height of the page
        
    Returns:
        List of box IDs in reading order
    """
    if not boxes:
        return []
    
    # Initialize categories
    title_blocks = []
    left_feature_blocks = []
    right_feature_blocks = []
    footer_blocks = []
    figure_blocks = []
    
    # Define layout zones
    title_threshold = page_height * 0.15
    footer_threshold = page_height * 0.70
    mid_x = page_width * 0.5
    
    # Categorize blocks
    for box in boxes:
        x1, y1, x2, y2 = box.bbox
        center_x = (x1 + x2) / 2
        width = x2 - x1
        
        # Separators stay with title
        if box.label == 'Separator':
            title_blocks.append(box)
        # Figures handled separately
        elif box.label in ['Figure', 'ImageRegion']:
            figure_blocks.append(box)
        # Wide text at top is title
        elif y1 < title_threshold and width > page_width * 0.6:
            title_blocks.append(box)
        # Footer text
        elif y1 > footer_threshold:
            footer_blocks.append(box)
        # Main content - split by column
        else:
            if center_x < mid_x:
                left_feature_blocks.append(box)
            else:
                right_feature_blocks.append(box)
    
    # Group feature blocks into clusters
    def cluster_by_proximity(blocks, gap_threshold=150):
        """Group blocks that are vertically close."""
        if not blocks:
            return []
        
        # Sort by Y position
        blocks = sorted(blocks, key=lambda b: b.bbox[1])
        
        clusters = []
        current_cluster = [blocks[0]]
        
        for i in range(1, len(blocks)):
            prev_bottom = blocks[i-1].bbox[3]
            curr_top = blocks[i].bbox[1]
            
            if curr_top - prev_bottom < gap_threshold:
                current_cluster.append(blocks[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [blocks[i]]
        
        if current_cluster:
            clusters.append(current_cluster)
        
        return clusters
    
    # Create feature clusters
    left_clusters = cluster_by_proximity(left_feature_blocks)
    right_clusters = cluster_by_proximity(right_feature_blocks)
    
    # Assign figures to nearest cluster
    for fig in figure_blocks:
        fig_center_x = (fig.bbox[0] + fig.bbox[2]) / 2
        fig_center_y = (fig.bbox[1] + fig.bbox[3]) / 2
        
        # Determine column
        target_clusters = left_clusters if fig_center_x < mid_x else right_clusters
        
        # Find nearest cluster by Y position
        if target_clusters:
            min_dist = float('inf')
            best_cluster_idx = 0
            
            for idx, cluster in enumerate(target_clusters):
                cluster_top = min(b.bbox[1] for b in cluster)
                cluster_bottom = max(b.bbox[3] for b in cluster)
                cluster_center_y = (cluster_top + cluster_bottom) / 2
                
                dist = abs(fig_center_y - cluster_center_y)
                if dist < min_dist:
                    min_dist = dist
                    best_cluster_idx = idx
            
            # Add figure to beginning of cluster (icons usually come first)
            target_clusters[best_cluster_idx].insert(0, fig)
    
    # Build final reading order
    reading_order = []
    
    # 1. Title and header
    title_blocks.sort(key=lambda b: (b.bbox[1], -(b.bbox[2] - b.bbox[0])))
    reading_order.extend([box.id for box in title_blocks])
    
    # 2. Process feature boxes in pairs (left column, then right column)
    max_rows = max(len(left_clusters), len(right_clusters)) if (left_clusters or right_clusters) else 0
    
    for row in range(max_rows):
        # Left column feature
        if row < len(left_clusters):
            cluster = sorted(left_clusters[row], key=lambda b: b.bbox[1])
            reading_order.extend([box.id for box in cluster])
        
        # Right column feature
        if row < len(right_clusters):
            cluster = sorted(right_clusters[row], key=lambda b: b.bbox[1])
            reading_order.extend([box.id for box in cluster])
    
    # 3. Footer content
    footer_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
    reading_order.extend([box.id for box in footer_blocks])
    
    return reading_order


