"""Visual Reordering Agent for determining reading order of elements."""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class VisualReorderingAgent:
    """Agent that determines reading order of elements on a page."""
    
    def __init__(self):
        """Initialize the visual reordering agent."""
        pass
    
    def determine_reading_order(
        self,
        elements: List[Dict[str, Any]],
        page_width: float,
        page_height: float
    ) -> List[Dict[str, Any]]:
        """Determine reading order of elements.
        
        For now, uses a simple column-based approach.
        Can be enhanced with visual LLM later.
        
        Args:
            elements: List of elements with bbox and type
            page_width: Width of the page
            page_height: Height of the page
            
        Returns:
            List of elements with reading_order added
        """
        # Simple column-based ordering
        # Group elements by x-coordinate (columns)
        column_threshold = page_width * 0.1  # 10% of page width
        
        # Add center coordinates
        for elem in elements:
            bbox = elem['bbox']
            elem['center_x'] = (bbox[0] + bbox[2]) / 2
            elem['center_y'] = (bbox[1] + bbox[3]) / 2
        
        # Sort by columns first (left to right), then top to bottom
        sorted_elements = sorted(
            elements,
            key=lambda e: (
                int(e['center_x'] / column_threshold),  # Column group
                -e['center_y']  # Top to bottom (negative because y increases downward)
            )
        )
        
        # Assign reading order
        for i, elem in enumerate(sorted_elements):
            elem['reading_order'] = i + 1
        
        return sorted_elements