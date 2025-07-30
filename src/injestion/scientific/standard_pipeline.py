"""Standard pipeline for academic/clinical PDF processing."""

from __future__ import annotations

import logging
import os
from typing import List, Optional
from pathlib import Path

from ..shared.base_pipeline import BasePDFPipeline
from ..shared.processing.layout_detector import LayoutDetectionPipeline
from ..shared.processing.overlap_resolver import no_overlap_pipeline, expand_boxes
from ..shared.processing.box import Box
from ..shared.processing.noop_consolidator import NoOpConsolidator
from src.interfaces import Block, Document
from ..shared.processing.text_extractor import extract_document_content
from ..shared.processing.reading_order import determine_reading_order_simple
from ..shared.storage.paths import stage_dir, save_json
from ..shared.config import IngestionConfig

logger = logging.getLogger(__name__)


class StandardPipeline(BasePDFPipeline):
    """Standard pipeline optimized for academic and clinical documents.
    
    Uses PubLayNet-based detection and functional box consolidation.
    """
    
    def process_pdf(self, pdf_path: str | os.PathLike[str]) -> Document:
        """Process a PDF file through the pipeline, always saving raw layouts."""
        pdf_path = Path(pdf_path)
        
        # Convert PDF to images
        logger.info(f"Converting {pdf_path.name} to images...")
        images = self._convert_to_images(pdf_path)
        
        # Run layout detection
        logger.info("Running layout detection...")
        layouts = self.detector.detect_images(images)
        
        # Always save raw layouts for the standard pipeline
        self._save_raw_layouts(layouts, pdf_path, images)
        
        # Apply consolidation
        logger.info("Applying box consolidation...")
        consolidated_layouts = self._apply_consolidation(layouts, images)
        
        # Save merged layouts if configured
        if self.config.save_intermediate_states:
            self._save_merged_layouts(consolidated_layouts, pdf_path)
        
        # Create document and extract content
        logger.info("Creating document structure...")
        document = self._create_document(consolidated_layouts, pdf_path, images)
        
        # Save outputs and visualize
        self._save_outputs(document, pdf_path)
        
        return document
    
    def _create_detector(self):
        """Create PubLayNet-based detector."""
        return LayoutDetectionPipeline(
            score_threshold=self.config.score_threshold,
            nms_threshold=self.config.nms_threshold
        )
    
    def _create_consolidator(self):
        """Standard pipeline uses functional consolidation via NoOpConsolidator."""
        return NoOpConsolidator()
    
    def _apply_consolidation(self, layouts: List, images: List) -> List:
        """Apply functional box consolidation."""
        # Store raw layouts for tracking
        self._last_raw_layouts = layouts
        
        consolidated_layouts = []
        
        for page_idx, page_layout in enumerate(layouts):
            # Convert to Box objects with deterministic IDs
            page_boxes = []
            for det_idx, layout in enumerate(page_layout):
                # Create deterministic ID based on page and detection index
                det_id = f"det_{page_idx}_{det_idx:03d}"
                box = Box(
                    id=det_id,
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
            
            # Expand boxes if configured
            if self.config.expand_boxes and page_boxes:
                page_boxes = expand_boxes(page_boxes, padding=self.config.box_padding)
            
            # Apply overlap resolution if configured
            if self.config.merge_overlapping and page_boxes:
                page_boxes = no_overlap_pipeline(
                    boxes=page_boxes,
                    merge_same_type_first=True,
                    merge_threshold=self.config.merge_threshold,
                    confidence_weight=self.config.confidence_weight,
                    area_weight=self.config.area_weight,
                    minor_overlap_threshold=self.config.minor_overlap_threshold,
                    same_type_merge_threshold=0.85  # Balanced threshold for text merging
                )
            
            consolidated_layouts.append(page_boxes)
        
        return consolidated_layouts
    
    def _create_document(self, layouts: List, pdf_path: Path, images: List) -> Document:
        """Convert processed layouts to Document."""
        all_blocks = []
        reading_order_by_page = []
        
        for page_idx, (page_boxes, image) in enumerate(zip(layouts, images)):
            # Determine reading order
            page_width = image.width
            reading_order = determine_reading_order_simple(page_boxes, page_width)
            reading_order_by_page.append(reading_order)
            
            # Convert to Block objects
            for box in page_boxes:
                block = Block(
                    id=box.id,
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
        
        # Create document with pipeline metadata
        document = Document(
            source_pdf=str(pdf_path),
            blocks=all_blocks,
            metadata={
                "pipeline": "standard",
                "detection_dpi": self.config.detection_dpi,
                "total_pages": len(layouts)
            },
            reading_order=reading_order_by_page,
            pipeline_metadata={
                "raw_detection_count": sum(len(page) for page in self._last_raw_layouts),
                "after_consolidation_count": sum(len(page) for page in layouts),
                "final_block_count": len(all_blocks),
                "box_tracking_enabled": True,
                "id_format": "det_<page>_<index> for detections, mrg_<source_id> for merges"
            }
        )
        
        # Extract text content
        document = extract_document_content(document, pdf_path, self.config.detection_dpi)
        
        return document
    
    def _save_outputs(self, document: Document, pdf_path: Path):
        """Save processing outputs."""
        output_dir = stage_dir("extracted", pdf_path)
        
        # Save document
        doc_path = output_dir / "content.json"
        document.save(doc_path)
        
        # Generate readable formats
        from ..shared.processing.document_formatter import (
            generate_readable_document,
            generate_text_only_document,
            generate_html_document
        )
        
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
    
    def _save_raw_layouts(self, layouts: List, pdf_path: Path, images: List):
        """Save raw layout detection results before any processing."""
        raw_dir = stage_dir("raw_layouts", pdf_path)
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Save raw layout data with deterministic IDs
        raw_data = []
        for page_idx, page_layout in enumerate(layouts):
            page_data = []
            for det_idx, layout in enumerate(page_layout):
                det_id = f"det_{page_idx}_{det_idx:03d}"
                page_data.append({
                    "id": det_id,
                    "bbox": [
                        layout.block.x_1,
                        layout.block.y_1,
                        layout.block.x_2,
                        layout.block.y_2,
                    ],
                    "label": str(layout.type) if layout.type else "Unknown",
                    "score": float(layout.score or 0.0),
                })
            raw_data.append(page_data)
        
        save_json(raw_data, raw_dir / "raw_layout_boxes.json")
        
        # Create visualization of raw layouts if configured
        if self.config.create_visualizations:
            from ..shared.visualization.layout_visualizer import visualize_page_layout
            viz_dir = raw_dir / "visualizations"
            viz_dir.mkdir(exist_ok=True)
            
            for page_idx, (page_layout, image) in enumerate(zip(layouts, images)):
                # Convert layouts to Box objects for visualization
                boxes = []
                for det_idx, layout in enumerate(page_layout):
                    det_id = f"det_{page_idx}_{det_idx:03d}"
                    box = Box(
                        id=det_id,
                        bbox=(
                            layout.block.x_1,
                            layout.block.y_1,
                            layout.block.x_2,
                            layout.block.y_2,
                        ),
                        label=str(layout.type) if layout.type else "Unknown",
                        score=float(layout.score or 0.0),
                    )
                    boxes.append(box)
                
                output_path = viz_dir / f"page_{page_idx + 1:03d}_raw_layout.png"
                visualize_page_layout(
                    image,
                    boxes,
                    title=f"Page {page_idx + 1} - Raw Detection ({len(boxes)} boxes)",
                    save_path=output_path,
                    show_labels=True,
                    show_reading_order=False,
                )