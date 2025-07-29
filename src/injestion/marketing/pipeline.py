"""Marketing document processing pipeline."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from pdf2image import convert_from_path

from .detector import MarketingLayoutDetector
from .vision_adjuster import MarketingVisionAdjuster
from ..models.box import Box
from ..models.document import Block, Document
from ..processing.overlap_resolver import no_overlap_pipeline
from ..processing.reading_order import determine_reading_order_simple
from ..processing.text_extractor import extract_document_content
from ..storage.paths import stage_dir, save_json, pages_dir
from ..visualization.layout_visualizer import visualize_document


class MarketingPipeline:
    """Complete pipeline for marketing document processing.
    
    This pipeline:
    1. Uses PrimaLayout for better marketing document detection
    2. Optionally applies vision LLM adjustments
    3. Integrates with existing document processing infrastructure
    """
    
    def __init__(
        self,
        use_vision_adjustment: bool = True,
        score_threshold: float = 0.15,
        nms_threshold: float = 0.4,
        detection_dpi: int = 400,
        create_visualizations: bool = True,
        apply_overlap_resolution: bool = False,  # Default to False for marketing
    ):
        """Initialize marketing pipeline.
        
        Parameters
        ----------
        use_vision_adjustment
            Whether to use vision LLM for layout improvements
        score_threshold
            Detection confidence threshold
        nms_threshold
            Non-maximum suppression threshold
        detection_dpi
            DPI for PDF rasterization
        create_visualizations
            Whether to create visualization outputs
        apply_overlap_resolution
            Whether to apply overlap resolution (can lose content if too aggressive)
        """
        self.use_vision_adjustment = use_vision_adjustment
        self.detection_dpi = detection_dpi
        self.create_visualizations = create_visualizations
        self.apply_overlap_resolution = apply_overlap_resolution
        
        # Initialize components
        self.detector = MarketingLayoutDetector(
            score_threshold=score_threshold,
            nms_threshold=nms_threshold
        )
        
        if use_vision_adjustment:
            self.adjuster = MarketingVisionAdjuster()
        else:
            self.adjuster = None
    
    def process_pdf(self, pdf_path: str | os.PathLike[str]) -> Document:
        """Process a marketing PDF document.
        
        Parameters
        ----------
        pdf_path
            Path to PDF file
            
        Returns
        -------
        Document object with detected and processed content
        """
        pdf_path = Path(pdf_path)
        
        # Convert PDF to images and save them
        print(f"Converting {pdf_path.name} to images...")
        images = convert_from_path(str(pdf_path), dpi=self.detection_dpi)
        
        # Save page images for visualization
        page_dir = pages_dir(pdf_path)
        page_dir.mkdir(parents=True, exist_ok=True)
        for idx, img in enumerate(images):
            img.save(page_dir / f"page-{idx:03}.png")
        
        # Run layout detection
        print("Running PrimaLayout detection...")
        layouts = self.detector.detect_images(images)
        
        # Save raw layouts for debugging
        self._save_raw_layouts(layouts, pdf_path, images)
        
        # Apply vision adjustments if enabled
        if self.use_vision_adjustment and self.adjuster:
            print("Applying vision LLM adjustments...")
            layouts = self.adjuster.adjust_layouts(layouts, images)
        
        # Convert to document format
        document = self._layouts_to_document(layouts, pdf_path, images)
        
        # Extract text content
        print("Extracting text content...")
        document = extract_document_content(
            document, 
            pdf_path, 
            self.detection_dpi,
            text_extractor="pymupdf"  # Use PyMuPDF for marketing docs
        )
        
        # Save outputs
        self._save_outputs(document, pdf_path)
        
        # Create visualizations if requested
        if self.create_visualizations:
            print("Creating visualizations...")
            visualize_document(
                document,
                pdf_path,
                show_labels=True,
                show_reading_order=True
            )
        
        return document
    
    def _layouts_to_document(
        self, 
        layouts: List,
        pdf_path: Path,
        images: List
    ) -> Document:
        """Convert layout detection results to Document format."""
        
        all_blocks = []
        reading_order_by_page = []
        
        for page_idx, (layout, image) in enumerate(zip(layouts, images)):
            # Convert to Box objects
            page_boxes = []
            for elem_idx, elem in enumerate(layout):
                box = Box(
                    id=f"p{page_idx}_e{elem_idx}",
                    bbox=(
                        elem.block.x_1,
                        elem.block.y_1,
                        elem.block.x_2,
                        elem.block.y_2
                    ),
                    label=str(elem.type),
                    score=float(elem.score)
                )
                page_boxes.append(box)
            
            # Apply overlap resolution if enabled
            if self.apply_overlap_resolution and page_boxes:
                page_boxes = no_overlap_pipeline(
                    boxes=page_boxes,
                    merge_same_type_first=True,
                    merge_threshold=0.1  # Only merge if 10%+ overlap
                )
            
            # Determine reading order
            page_width = image.width
            reading_order = determine_reading_order_simple(page_boxes, page_width)
            reading_order_by_page.append(reading_order)
            
            # Convert to Block objects
            for box in page_boxes:
                block = Block(
                    id=box.id,
                    page_index=page_idx,
                    role=self._map_role(box.label),
                    bbox=box.bbox,
                    metadata={
                        "score": box.score,
                        "detection_dpi": self.detection_dpi,
                        "detector": "PrimaLayout",
                        "adjusted": self.use_vision_adjustment
                    }
                )
                all_blocks.append(block)
        
        # Create document
        return Document(
            source_pdf=str(pdf_path),
            blocks=all_blocks,
            metadata={
                "pipeline": "marketing",
                "detection_dpi": self.detection_dpi,
                "vision_adjusted": self.use_vision_adjustment,
                "total_pages": len(layouts)
            },
            reading_order=reading_order_by_page
        )
    
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
        # Save to marketing-specific directory
        output_dir = stage_dir("marketing", pdf_path)
        
        # Save document
        doc_path = output_dir / "document.json"
        document.save(doc_path)
        
        # Save summary
        summary = {
            "source": str(pdf_path),
            "pages": document.metadata.get("total_pages", 0),
            "blocks": len(document.blocks),
            "blocks_by_type": {},
            "vision_adjusted": self.use_vision_adjustment
        }
        
        for block in document.blocks:
            role = block.role
            summary["blocks_by_type"][role] = summary["blocks_by_type"].get(role, 0) + 1
        
        save_json(summary, output_dir / "summary.json")
        print(f"\nOutputs saved to: {output_dir}")
    
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
        
        # Create visualization of raw layouts
        if self.create_visualizations:
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
            
            print(f"  Raw layout visualizations saved to: {viz_dir}")