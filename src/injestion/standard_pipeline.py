"""Standard pipeline for academic/clinical PDF processing."""

from __future__ import annotations

from typing import List, Optional
from pathlib import Path

from .base_pipeline import BasePDFPipeline
from .processing.layout_detector import LayoutDetectionPipeline
from .processing.overlap_resolver import no_overlap_pipeline, expand_boxes
from .processing.box import Box
from src.interfaces import Block, Document
from .processing.text_extractor import extract_document_content
from .processing.reading_order import determine_reading_order_simple
from .storage.paths import stage_dir, save_json
from .config import IngestionConfig
import uuid


class StandardPipeline(BasePDFPipeline):
    """Standard pipeline optimized for academic and clinical documents.
    
    Uses PubLayNet-based detection and functional box consolidation.
    """
    
    def _create_detector(self):
        """Create PubLayNet-based detector."""
        return LayoutDetectionPipeline(
            score_threshold=self.config.score_threshold,
            nms_threshold=self.config.nms_threshold
        )
    
    def _create_consolidator(self):
        """Standard pipeline uses functional consolidation."""
        return None  # We use functional approach
    
    def _apply_consolidation(self, layouts: List, images: List) -> List:
        """Apply functional box consolidation."""
        consolidated_layouts = []
        
        for page_idx, page_layout in enumerate(layouts):
            # Convert to Box objects
            page_boxes = [
                Box(
                    id=str(uuid.uuid4())[:8],
                    bbox=(
                        layout.block.x_1,
                        layout.block.y_1,
                        layout.block.x_2,
                        layout.block.y_2,
                    ),
                    label=str(layout.type) if layout.type else "Unknown",
                    score=float(layout.score or 0.0),
                )
                for layout in page_layout
            ]
            
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
                    area_weight=self.config.area_weight
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
        
        # Create document
        document = Document(
            source_pdf=str(pdf_path),
            blocks=all_blocks,
            metadata={
                "pipeline": "standard",
                "detection_dpi": self.config.detection_dpi,
                "total_pages": len(layouts)
            },
            reading_order=reading_order_by_page
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
        from .processing.document_formatter import (
            generate_readable_document,
            generate_text_only_document,
            generate_html_document
        )
        
        generate_readable_document(document, output_dir / "document.md", include_images=True)
        generate_text_only_document(document, output_dir / "document.txt", include_placeholders=True)
        generate_html_document(document, output_dir / "document.html", include_images=True)
        
        # Create visualizations if configured
        if self.config.create_visualizations:
            from .visualization.layout_visualizer import visualize_document
            visualize_document(
                document,
                pdf_path,
                show_labels=True,
                show_reading_order=True
            )
        
        print(f"\nOutputs saved to: {output_dir}")