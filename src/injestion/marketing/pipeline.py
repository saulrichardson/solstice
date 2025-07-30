"""Marketing document processing pipeline - Simplified version."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

from .detector import MarketingLayoutDetector
from .consolidation import BoxConsolidator
from ..processing.box import Box
# already correct; ensure not using models.document; no change
from .reading_order import determine_marketing_reading_order
from ..processing.text_extractor import extract_document_content
from ..storage.paths import stage_dir, save_json, pages_dir
from ..visualization.layout_visualizer import visualize_document
from ..config import get_config, IngestionConfig
from ..base_pipeline import BasePDFPipeline
from src.interfaces import Block, Document
import layoutparser as lp
import uuid


class MarketingPipeline(BasePDFPipeline):
    """Complete pipeline for marketing document processing.
    
    This pipeline:
    1. Uses PrimaLayout for better marketing document detection
    2. Applies advanced box consolidation and overlap resolution
    3. Integrates with existing document processing infrastructure
    """
    
    def __init__(self, config: Optional[IngestionConfig] = None):
        """Initialize marketing pipeline.
        
        Parameters
        ----------
        config
            Optional IngestionConfig instance. If not provided, uses marketing preset.
        """
        # Use marketing preset if no config provided
        if config is None:
            config = get_config('marketing')
        super().__init__(config)
    
    def _create_detector(self) -> MarketingLayoutDetector:
        """Create PrimaLayout-based detector for marketing documents."""
        return MarketingLayoutDetector(
            score_threshold=self.config.score_threshold,
            nms_threshold=self.config.nms_threshold
        )
    
    def _create_consolidator(self) -> BoxConsolidator:
        """Create box consolidator for marketing layouts."""
        return BoxConsolidator(
            merge_threshold=self.config.merge_threshold,
            expand_padding=self.config.box_padding if self.config.expand_boxes else 0.0
        )
    
    
    def _apply_consolidation(self, layouts: List, images: List) -> List[List[Box]]:
        """Apply consolidation to layouts using the BoxConsolidator.
        
        Returns List[List[Box]] for consistency with StandardPipeline.
        """
        import uuid
        
        consolidated_layouts = []
        
        for page_idx, layout in enumerate(layouts):
            # Convert to Box objects
            boxes = []
            for elem in layout:
                box = Box(
                    id=str(uuid.uuid4())[:8],
                    bbox=(
                        elem.block.x_1,
                        elem.block.y_1,
                        elem.block.x_2,
                        elem.block.y_2
                    ),
                    label=str(elem.type),
                    score=float(elem.score)
                )
                boxes.append(box)
            
            # Apply consolidation if enabled
            if self.config.merge_overlapping and boxes:
                # Fail-fast: require valid image dimensions
                if page_idx >= len(images):
                    raise IndexError(f"Page {page_idx} not found in images list")
                
                image_width = images[page_idx].width
                image_height = images[page_idx].height
                
                if image_width <= 0 or image_height <= 0:
                    raise ValueError(f"Invalid image dimensions on page {page_idx}: {image_width}x{image_height}")
                
                # Use the consolidator to handle all box operations
                boxes = self.consolidator.consolidate_boxes(
                    boxes, 
                    image_width=image_width,
                    image_height=image_height
                )
            
            # Return Box objects directly
            consolidated_layouts.append(boxes)
        
        return consolidated_layouts
    
    def _create_document(self, layouts: List[List[Box]], pdf_path: Path, images: List) -> Document:
        """Convert layout detection results to Document format.
        
        Now expects layouts as List[List[Box]] for consistency.
        """
        all_blocks = []
        reading_order_by_page = []
        
        for page_idx, (page_boxes, image) in enumerate(zip(layouts, images)):
            # page_boxes is already a list of Box objects
            
            # Determine reading order using marketing-specific algorithm
            page_width = image.width
            page_height = image.height
            reading_order = determine_marketing_reading_order(page_boxes, page_width, page_height)
            reading_order_by_page.append(reading_order)
            
            # Convert to Block objects
            for box_idx, box in enumerate(page_boxes):
                metadata = {
                    "score": box.score,
                    "detection_dpi": self.config.detection_dpi,
                    "detector": "PrimaLayout"
                }
                
                block = Block(
                    id=box.id,
                    page_index=page_idx,
                    role=self._map_role(box.label),
                    bbox=box.bbox,
                    metadata=metadata
                )
                all_blocks.append(block)
        
        # Create document
        document = Document(
            source_pdf=str(pdf_path),
            blocks=all_blocks,
            metadata={
                "pipeline": "marketing",
                "detection_dpi": self.config.detection_dpi,
                "total_pages": len(layouts)
            },
            reading_order=reading_order_by_page
        )
        
        # Extract text content
        document = extract_document_content(document, pdf_path, self.config.detection_dpi)
        
        return document
    
    def _map_role(self, prima_label: str) -> str:
        """Map PrimaLayout labels to document roles."""
        mapping = {
            "TextRegion": "Text",
            "ImageRegion": "Figure",
            "TableRegion": "Table",
            "MathsRegion": "Formula",
            "SeparatorRegion": "Separator",
            "OtherRegion": "Other"
        }
        return mapping.get(prima_label, prima_label)
    
    def _save_outputs(self, document: Document, pdf_path: Path):
        """Save processing outputs."""
        output_dir = stage_dir("extracted", pdf_path)
        
        # Save document
        doc_path = output_dir / "content.json"
        document.save(doc_path)
        
        # Generate readable formats
        from ..processing.document_formatter import (
            generate_readable_document,
            generate_text_only_document,
            generate_html_document
        )
        
        generate_readable_document(document, output_dir / "document.md", include_images=True)
        generate_text_only_document(document, output_dir / "document.txt", include_placeholders=True)
        generate_html_document(document, output_dir / "document.html", include_images=True)
        
        # Create visualizations if configured
        if self.config.create_visualizations:
            visualize_document(
                document,
                pdf_path,
                show_labels=True,
                show_reading_order=True
            )
        
        logger.info(f"Outputs saved to: {output_dir}")
    
    def _save_raw_layouts(self, layouts: List, pdf_path: Path, images: List):
        """Save raw layout detection results before any processing."""
        raw_dir = stage_dir("raw_marketing", pdf_path)
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        # Save raw layout data
        raw_data = []
        for page_idx, layout in enumerate(layouts):
            page_data = []
            for elem in layout:
                page_data.append({
                    "type": str(elem.type),
                    "bbox": [elem.block.x_1, elem.block.y_1, elem.block.x_2, elem.block.y_2],
                    "score": float(elem.score)
                })
            raw_data.append(page_data)
        
        save_json(raw_data, raw_dir / "raw_layouts.json")
        
        # Create visualization of raw layouts (always)
        viz_dir = raw_dir / "visualizations"
        viz_dir.mkdir(exist_ok=True)
        
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        for page_idx, (layout, image) in enumerate(zip(layouts, images)):
            fig, ax = plt.subplots(1, 1, figsize=(12, 16))
            ax.imshow(image)
            
            colors = {
                "TextRegion": "blue",
                "ImageRegion": "green",
                "TableRegion": "orange",
                "SeparatorRegion": "red",
                "OtherRegion": "purple"
            }
            
            for i, elem in enumerate(layout):
                rect = patches.Rectangle(
                    (elem.block.x_1, elem.block.y_1),
                    elem.block.x_2 - elem.block.x_1,
                    elem.block.y_2 - elem.block.y_1,
                    linewidth=1,
                    edgecolor=colors.get(str(elem.type), "black"),
                    facecolor='none',
                    alpha=0.6
                )
                ax.add_patch(rect)
                
                # Add number for reference
                ax.text(
                    elem.block.x_1 + 5,
                    elem.block.y_1 + 20,
                    str(i+1),
                    color='white',
                    fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor=colors.get(str(elem.type), "black"), alpha=0.8)
                )
            
            ax.set_xlim(0, image.width)
            ax.set_ylim(image.height, 0)
            ax.axis('off')
            plt.title(f"Raw PrimaLayout Detection - Page {page_idx + 1} ({len(layout)} regions)")
            plt.tight_layout()
            
            output_path = viz_dir / f"page_{page_idx + 1:03d}_raw.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
        
        logger.info(f"Raw layout visualizations saved to: {viz_dir}")
