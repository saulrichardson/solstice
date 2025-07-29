"""No-operation consolidator for pipelines that use functional consolidation."""

from typing import List, Optional
from ..processing.box import Box


class NoOpConsolidator:
    """A consolidator that performs no operations.
    
    Used by pipelines that handle consolidation through functional approaches
    rather than object-oriented consolidation.
    """
    
    def consolidate_boxes(self, 
                         boxes: List[Box], 
                         image_width: int,
                         image_height: int) -> List[Box]:
        """Return boxes unchanged.
        
        Args:
            boxes: Input boxes
            image_width: Width of the image (required but unused)
            image_height: Height of the image (required but unused)
            
        Returns:
            Original boxes without modification
        """
        if image_width <= 0 or image_height <= 0:
            raise ValueError(f"Invalid image dimensions: {image_width}x{image_height}")
        return boxes