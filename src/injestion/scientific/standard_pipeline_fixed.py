"""Fixed StandardPipeline with consistent ID management."""

import logging
from pathlib import Path
from typing import List, Tuple
import os

from ..shared.processing.document_formatter import (
    generate_readable_document,
    generate_text_only_document,
    generate_html_document
)
from ..shared.processing.layout_detector import LayoutDetectionPipeline
from ..shared.processing.overlap_resolver import no_overlap_pipeline, expand_boxes
from ..shared.processing.box import Box
from ..shared.processing.noop_consolidator import NoOpConsolidator
from ..shared.processing.box_id_manager import BoxIDManager
from src.interfaces import Block, Document
from ..shared.processing.text_extractor import extract_document_content
from ..shared.processing.reading_order import determine_reading_order_simple
from ..shared.storage.paths import stage_dir, save_json
from ..shared.config import IngestionConfig

logger = logging.getLogger(__name__)


class StandardPipelineFixed:
    """Fixed pipeline with consistent ID management throughout."""
    
    def __init__(self, config: IngestionConfig = None):
        """Initialize pipeline with configuration."""
        self.config = config or IngestionConfig()
        self.detector = self._create_detector()
        self.consolidator = NoOpConsolidator()
        self._last_raw_layouts = []
        self.id_manager = BoxIDManager()
    
    def process_pdf(self, pdf_path: str | os.PathLike[str]) -> Document:
        """Process a PDF file through the pipeline with consistent IDs."""
        pdf_path = Path(pdf_path)
        
        # Convert PDF to images
        logger.info(f"Converting {pdf_path.name} to images...")
        images = self._convert_to_images(pdf_path)
        
        # Run layout detection
        logger.info("Running layout detection...")
        layouts = self.detector.detect_images(images)
        
        # Save raw layouts
        self._save_raw_layouts(layouts, pdf_path, images)
        
        # Apply consolidation with ID management
        logger.info("Applying box consolidation with ID tracking...")
        consolidated_layouts = self._apply_consolidation_with_ids(layouts, images)
        
        # Save merged layouts if configured
        if self.config.save_intermediate_states:
            self._save_merged_layouts(consolidated_layouts, pdf_path)
        
        # Create document and extract content
        logger.info("Creating document structure with consistent IDs...")
        document = self._create_document_with_ids(consolidated_layouts, pdf_path, images)
        
        # Save outputs and visualize
        self._save_outputs(document, pdf_path)
        
        return document
    
    def _apply_consolidation_with_ids(self, layouts: List, images: List) -> List[List[Box]]:
        """Apply consolidation pipeline with ID management."""
        consolidated_layouts = []
        
        for page_idx, page_layout in enumerate(layouts):
            # Convert to Box objects with temporary IDs
            page_boxes = []
            for det_idx, layout in enumerate(page_layout):
                temp_id = f"det_{page_idx}_{det_idx:03d}"
                box = Box(
                    id=temp_id,
                    bbox=(
                        layout.block.x_1,
                        layout.block.y_1,
                        layout.block.x_2,
                        layout.block.y_2,
                    ),
                    label=str(layout.type) if layout.type else "Unknown",
                    score=float(layout.score or 0.0),
                    page_index=page_idx,
                )
                page_boxes.append(box)
            
            # Assign final IDs immediately after detection
            page_boxes = self.id_manager.assign_final_ids(page_boxes, page_idx)
            
            # Expand boxes if configured
            if self.config.expand_boxes and page_boxes:
                page_boxes = expand_boxes(page_boxes, padding=self.config.box_padding)
            
            # Apply overlap resolution with ID tracking
            if self.config.merge_overlapping and page_boxes:
                page_boxes = self._apply_overlap_resolution_with_ids(page_boxes)
            
            consolidated_layouts.append(page_boxes)
        
        return consolidated_layouts
    
    def _apply_overlap_resolution_with_ids(self, boxes: List[Box]) -> List[Box]:
        """Apply overlap resolution while tracking ID changes."""
        # Custom overlap resolver that uses our ID manager
        # For now, use the standard resolver and track deletions
        original_ids = {box.id for box in boxes}
        
        resolved_boxes = no_overlap_pipeline(
            boxes=boxes,
            merge_same_type_first=True,
            merge_threshold=self.config.merge_threshold,
            confidence_weight=self.config.confidence_weight,
            area_weight=self.config.area_weight,
            minor_overlap_threshold=self.config.minor_overlap_threshold,
            same_type_merge_threshold=0.85
        )
        
        # Track deletions
        resolved_ids = {box.id for box in resolved_boxes}
        for deleted_id in original_ids - resolved_ids:
            self.id_manager.register_deletion(deleted_id)
        
        return resolved_boxes
    
    def _create_document_with_ids(self, layouts: List, pdf_path: Path, images: List) -> Document:
        """Create document with consistent IDs in reading order."""
        all_blocks = []
        reading_order_by_page = []
        
        for page_idx, (page_boxes, image) in enumerate(zip(layouts, images)):
            # Determine reading order using current box IDs
            page_width = image.width
            page_height = image.height
            raw_reading_order = determine_reading_order_simple(page_boxes, page_width, page_height)
            
            # Update reading order to ensure it uses final IDs
            final_reading_order = self.id_manager.update_reading_order(raw_reading_order)
            reading_order_by_page.append(final_reading_order)
            
            # Convert to Block objects (IDs are already final)
            for box in page_boxes:
                block = Block(
                    id=box.id,  # This is already the final ID
                    page_index=page_idx,
                    role=box.label,
                    bbox=box.bbox,
                    metadata={
                        "score": box.score,
                        "detection_dpi": self.config.detection_dpi,
                        "detector": "PubLayNet"
                    }
                )
                all_blocks.append(block)
        
        # Create document
        document = Document(
            source_pdf=str(pdf_path),
            blocks=all_blocks,
            metadata={
                "pipeline": "standard_fixed",
                "detection_dpi": self.config.detection_dpi,
                "total_pages": len(layouts),
                "id_transformations": self.id_manager.get_transformation_report()
            },
            reading_order=reading_order_by_page,
            pipeline_metadata={
                "raw_detection_count": sum(len(page) for page in self._last_raw_layouts),
                "after_consolidation_count": sum(len(page) for page in layouts),
                "final_block_count": len(all_blocks),
                "id_system": "consistent_block_ids"
            }
        )
        
        # Validate consistency
        self.id_manager.validate_document(all_blocks, reading_order_by_page)
        
        # Extract text content
        document = extract_document_content(document, pdf_path, self.config.detection_dpi)
        
        return document
    
    # ... (include other methods from original StandardPipeline)
    def _create_detector(self):
        """Create PubLayNet-based detector."""
        return LayoutDetectionPipeline(
            score_threshold=self.config.score_threshold,
            nms_threshold=self.config.nms_threshold
        )
    
    def _convert_to_images(self, pdf_path: Path) -> List:
        """Convert PDF to images at specified DPI."""
        from ..shared.utils.pdf_utils import pdf_to_images
        images_dir = stage_dir("pages", pdf_path)
        return pdf_to_images(
            pdf_path,
            output_dir=images_dir,
            dpi=self.config.detection_dpi
        )
    
    def _save_raw_layouts(self, layouts: List, pdf_path: Path, images: List):
        """Save raw layout detection results."""
        self._last_raw_layouts = layouts
        raw_dir = stage_dir("raw_layouts", pdf_path)
        
        raw_data = []
        for page_idx, page_layout in enumerate(layouts):
            page_data = []
            for det_idx, layout in enumerate(page_layout):
                page_data.append({
                    "id": f"det_{page_idx}_{det_idx:03d}",
                    "bbox": [
                        layout.block.x_1,
                        layout.block.y_1,
                        layout.block.x_2,
                        layout.block.y_2,
                    ],
                    "label": str(layout.type) if layout.type else "Unknown",
                    "score": float(layout.score or 0.0)
                })
            raw_data.append(page_data)
        
        save_json(raw_data, raw_dir / "raw_layout_boxes.json")
    
    def _save_merged_layouts(self, layouts: List[List[Box]], pdf_path: Path):
        """Save merged/consolidated layouts."""
        merged_dir = stage_dir("merged", pdf_path)
        
        merged_data = []
        for page_boxes in layouts:
            page_data = []
            for box in page_boxes:
                page_data.append({
                    "id": box.id,  # This is now the final ID
                    "bbox": list(box.bbox),
                    "label": box.label,
                    "score": box.score
                })
            merged_data.append(page_data)
        
        save_json(merged_data, merged_dir / "merged_boxes.json")
    
    def _save_outputs(self, document: Document, pdf_path: Path):
        """Save processing outputs."""
        output_dir = stage_dir("extracted", pdf_path)
        
        # Save document
        doc_path = output_dir / "content.json"
        document.save(doc_path)
        
        # Generate readable formats
        generate_readable_document(document, output_dir / "document.md", include_images=True)
        generate_text_only_document(document, output_dir / "document.txt", include_placeholders=True)
        generate_html_document(document, output_dir / "document.html", include_images=True)
        
        # Create visualizations if configured
        if self.config.create_visualizations:
            from ..shared.visualization.layout_visualizer import visualize_document
            visualize_document(
                document,
                pdf_path,
                show_labels=True,
                show_reading_order=True
            )
        
        logger.info(f"Outputs saved to: {output_dir}")