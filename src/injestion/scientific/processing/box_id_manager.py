"""Centralized ID management for document processing pipeline.

This module ensures consistent IDs throughout the entire pipeline, solving the
problem of mismatched IDs between detection, merging, and reading order.
"""

import hashlib
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BoxIDMapping:
    """Tracks ID transformations through the pipeline."""
    original_id: str  # Original detection ID (e.g., "det_0_001")
    final_id: str     # Final stable ID (e.g., "block_0_001")
    merged_from: List[str] = None  # IDs that were merged into this box
    
    def __post_init__(self):
        if self.merged_from is None:
            self.merged_from = []


class BoxIDManager:
    """Manages consistent box IDs throughout the processing pipeline.
    
    Key principles:
    1. Assign final IDs early (after detection)
    2. Track transformations (merging, filtering)
    3. Update reading order to use final IDs
    4. Provide audit trail for debugging
    """
    
    def __init__(self):
        self.mappings: Dict[str, BoxIDMapping] = {}
        self.final_to_original: Dict[str, str] = {}
        self.deleted_ids: Set[str] = set()
        self._id_counter = 0
    
    def assign_final_ids(self, boxes: List['Box'], page_idx: int) -> List['Box']:
        """Assign permanent IDs to boxes right after detection.
        
        Args:
            boxes: List of detected boxes with temporary IDs
            page_idx: Page index for ID generation
            
        Returns:
            Boxes with final IDs assigned
        """
        updated_boxes = []
        
        for box in boxes:
            # Generate deterministic final ID
            final_id = f"block_{page_idx}_{self._id_counter:03d}"
            self._id_counter += 1
            
            # Create mapping
            mapping = BoxIDMapping(
                original_id=box.id,
                final_id=final_id
            )
            self.mappings[box.id] = mapping
            self.final_to_original[final_id] = box.id
            
            # Update box with final ID
            box.id = final_id
            updated_boxes.append(box)
            
            logger.debug(f"Assigned {final_id} to original {mapping.original_id}")
        
        return updated_boxes
    
    def register_merge(self, merged_box: 'Box', source_boxes: List['Box']) -> 'Box':
        """Register a merge operation and assign appropriate ID.
        
        Args:
            merged_box: The result of merging
            source_boxes: Boxes that were merged
            
        Returns:
            Merged box with correct ID
        """
        # Use the ID of the highest-scoring source box
        primary_box = max(source_boxes, key=lambda b: (b.score or 0, b.area))
        merged_box.id = primary_box.id
        
        # Track the merge in mappings
        primary_mapping = self.mappings.get(primary_box.id)
        if primary_mapping:
            # Record which boxes were merged
            for box in source_boxes:
                if box.id != primary_box.id:
                    primary_mapping.merged_from.append(box.id)
                    self.deleted_ids.add(box.id)
        
        logger.debug(f"Merged {[b.id for b in source_boxes]} into {merged_box.id}")
        
        return merged_box
    
    def register_deletion(self, box_id: str):
        """Register that a box was deleted (e.g., filtered out)."""
        self.deleted_ids.add(box_id)
        logger.debug(f"Deleted box {box_id}")
    
    def update_reading_order(self, reading_order: List[str]) -> List[str]:
        """Update reading order to use final IDs.
        
        Args:
            reading_order: List of IDs (could be original or intermediate)
            
        Returns:
            Reading order with final IDs
        """
        updated_order = []
        
        for old_id in reading_order:
            # Skip deleted boxes
            if old_id in self.deleted_ids:
                continue
            
            # If this is already a final ID, keep it
            if old_id.startswith("block_"):
                updated_order.append(old_id)
            # Otherwise, look up the final ID
            elif old_id in self.mappings:
                final_id = self.mappings[old_id].final_id
                if final_id not in self.deleted_ids:
                    updated_order.append(final_id)
            else:
                logger.warning(f"Unknown ID in reading order: {old_id}")
        
        return updated_order
    
    def get_transformation_report(self) -> Dict:
        """Get a report of all ID transformations for debugging."""
        return {
            "total_mappings": len(self.mappings),
            "deleted_count": len(self.deleted_ids),
            "merges": [
                {
                    "final_id": m.final_id,
                    "original_id": m.original_id,
                    "merged_from": m.merged_from
                }
                for m in self.mappings.values()
                if m.merged_from
            ]
        }
    
    def validate_document(self, blocks: List['Block'], reading_orders: List[List[str]]) -> bool:
        """Validate that all IDs in the document are consistent.
        
        Args:
            blocks: All blocks in the document
            reading_orders: Reading order for each page
            
        Returns:
            True if valid, raises exception if not
        """
        # Collect all block IDs
        block_ids = {block.id for block in blocks}
        
        # Check that all reading order IDs exist in blocks
        for page_idx, page_order in enumerate(reading_orders):
            for ro_id in page_order:
                if ro_id not in block_ids:
                    raise ValueError(
                        f"Reading order ID '{ro_id}' on page {page_idx} "
                        f"not found in blocks. Available IDs: {sorted(block_ids)}"
                    )
        
        # Check that all blocks have final IDs
        for block in blocks:
            if not block.id.startswith("block_"):
                raise ValueError(
                    f"Block has non-final ID: {block.id}. "
                    "All blocks should have IDs starting with 'block_'"
                )
        
        logger.info("Document validation passed - all IDs are consistent")
        return True