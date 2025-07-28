"""Complete PDF ingestion pipeline with visual reasoning support.

This pipeline processes PDFs end-to-end:
1. Layout detection
2. Visual reordering
3. Content extraction (text + images)
4. Structured output for LLM consumption
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
from pdf2image import convert_from_path
import pdfplumber

from .layout_pipeline import LayoutDetectionPipeline
from .agent.visual_reordering_agent import VisualReorderingAgent
from .extractors.component_extractors import ComponentRouter

logger = logging.getLogger(__name__)


class CompletePDFIngestionPipeline:
    """Complete pipeline for PDF processing with visual reasoning support."""
    
    def __init__(
        self,
        output_base_dir: str = "output",
        detection_dpi: int = 200,
        extraction_dpi: int = 300,
        save_page_images: bool = False,
        chunk_size: int = 2000  # tokens
    ):
        """Initialize the pipeline.
        
        Args:
            output_base_dir: Base directory for outputs
            detection_dpi: DPI for layout detection
            extraction_dpi: DPI for image extraction
            save_page_images: Whether to save full page images
            chunk_size: Target chunk size in tokens
        """
        self.output_base = Path(output_base_dir)
        self.detection_dpi = detection_dpi
        self.extraction_dpi = extraction_dpi
        self.save_page_images = save_page_images
        self.chunk_size = chunk_size
        
        # Initialize components
        self.layout_detector = LayoutDetectionPipeline(
            model=None,  # Uses default
            score_threshold=0.5,
            detection_dpi=self.detection_dpi
        )
        self.reordering_agent = VisualReorderingAgent()
        self.extractor = ComponentRouter()
    
    def _cuda_available(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def process_pdf(
        self,
        pdf_path: str | Path,
        doc_name: Optional[str] = None,
        **kwargs
    ) -> Path:
        """Process a PDF end-to-end.
        
        Args:
            pdf_path: Path to PDF file
            doc_name: Optional name for output directory
            **kwargs: Additional options
            
        Returns:
            Path to output directory
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Setup output directory
        if doc_name is None:
            doc_name = pdf_path.stem
        output_dir = self.output_base / doc_name
        
        logger.info(f"Processing PDF: {pdf_path}")
        logger.info(f"Output directory: {output_dir}")
        
        try:
            # 1. Setup directories
            self._setup_directories(output_dir)
            
            # 2. Layout detection
            logger.info("Step 1: Layout detection...")
            layout_results = self._detect_layout(pdf_path)
            
            # 3. Visual reordering
            logger.info("Step 2: Visual reordering...")
            ordered_results = self._apply_visual_reordering(layout_results)
            
            # 4. Extract content
            logger.info("Step 3: Content extraction...")
            content = self._extract_all_content(
                pdf_path,
                ordered_results,
                output_dir
            )
            
            # 5. Save outputs
            logger.info("Step 4: Saving outputs...")
            self._save_outputs(content, output_dir)
            
            # 6. Create LLM packages
            logger.info("Step 5: Creating LLM packages...")
            self._create_llm_packages(content, output_dir)
            
            # 7. Save page images if requested
            if self.save_page_images:
                logger.info("Step 6: Saving page images...")
                self._save_page_images(pdf_path, output_dir)
            
            logger.info(f"✓ Pipeline complete! Output saved to: {output_dir}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def _setup_directories(self, output_dir: Path):
        """Create output directory structure."""
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "pages").mkdir(exist_ok=True)
        (output_dir / "figures").mkdir(exist_ok=True)
        (output_dir / "tables").mkdir(exist_ok=True)
        (output_dir / "chunks").mkdir(exist_ok=True)
    
    def _detect_layout(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Run layout detection on PDF."""
        # Get layout results from LayoutDetectionPipeline
        layouts = self.layout_detector.process_pdf(pdf_path)
        
        # Convert to our expected format
        results = []
        for page_num, layout in enumerate(layouts, 1):
            # Get page dimensions from first detection (approximate)
            page_width = 1700  # Default assumption
            page_height = 2200  # Default assumption
            
            layout_boxes = []
            for element in layout:
                # Extract bounding box
                x1, y1, x2, y2 = element.coordinates
                
                layout_boxes.append({
                    'type': element.type,
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'confidence': float(element.score) if hasattr(element, 'score') else 1.0
                })
                
                # Update page dimensions based on detections
                page_width = max(page_width, x2)
                page_height = max(page_height, y2)
            
            results.append({
                'page_num': page_num,
                'page_width': page_width,
                'page_height': page_height,
                'layout_boxes': layout_boxes
            })
        
        return results
    
    def _apply_visual_reordering(
        self,
        layout_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply visual reordering to layout results."""
        ordered_results = []
        
        for page_result in layout_results:
            # Extract elements
            elements = []
            
            # Add all detected elements
            for box in page_result.get('layout_boxes', []):
                elements.append({
                    'type': box['type'].lower(),
                    'bbox': box['bbox'],
                    'confidence': box['confidence'],
                    'text': box.get('text', ''),
                    'original_box': box
                })
            
            # Apply reordering
            ordered_elements = self.reordering_agent.determine_reading_order(
                elements,
                page_result['page_width'],
                page_result['page_height']
            )
            
            ordered_results.append({
                'page_num': page_result['page_num'],
                'page_width': page_result['page_width'],
                'page_height': page_result['page_height'],
                'ordered_elements': ordered_elements,
                'original_result': page_result
            })
        
        return ordered_results
    
    def _extract_all_content(
        self,
        pdf_path: Path,
        ordered_results: List[Dict[str, Any]],
        output_dir: Path
    ) -> Dict[str, Any]:
        """Extract all content from PDF."""
        content = {
            "metadata": self._create_metadata(pdf_path),
            "pages": []
        }
        
        # Convert PDF pages to images for figure/table extraction
        logger.info("Converting PDF to images...")
        pdf_images = convert_from_path(pdf_path, dpi=self.extraction_dpi)
        
        for page_data in ordered_results:
            page_num = page_data['page_num']
            page_image = pdf_images[page_num - 1] if page_num <= len(pdf_images) else None
            
            page_content = {
                "page_num": page_num,
                "dimensions": {
                    "width": page_data['page_width'],
                    "height": page_data['page_height']
                },
                "elements": []
            }
            
            # Process each element in reading order
            for idx, element in enumerate(page_data['ordered_elements']):
                element_data = self._process_element(
                    element,
                    pdf_path,
                    page_num,
                    idx,
                    output_dir,
                    page_image
                )
                if element_data:
                    page_content["elements"].append(element_data)
            
            content["pages"].append(page_content)
        
        return content
    
    def _process_element(
        self,
        element: Dict[str, Any],
        pdf_path: Path,
        page_num: int,
        element_idx: int,
        output_dir: Path,
        page_image: Optional[Image.Image]
    ) -> Optional[Dict[str, Any]]:
        """Process a single element."""
        element_type = element['type'].lower()
        bbox = element['bbox']
        
        try:
            if element_type in ['text', 'title', 'list']:
                # Extract text
                result = self.extractor.extract_component(
                    element_type,
                    pdf_path,
                    page_num,
                    bbox,
                    detection_dpi=self.detection_dpi
                )
                
                return {
                    "type": element_type,
                    "content": result.get('text', ''),
                    "bbox": bbox,
                    "reading_order": element['reading_order'],
                    "confidence": element.get('confidence', 0)
                }
            
            elif element_type == 'figure':
                # Extract figure as image
                fig_path = output_dir / "figures" / f"figure_p{page_num}_{element_idx}.png"
                
                if page_image:
                    # Scale bbox to extraction DPI
                    scale = self.extraction_dpi / self.detection_dpi
                    scaled_bbox = tuple(int(coord * scale) for coord in bbox)
                    
                    # Crop and save
                    figure_img = page_image.crop(scaled_bbox)
                    figure_img.save(fig_path)
                    
                    return {
                        "type": "figure",
                        "path": str(fig_path.relative_to(output_dir)),
                        "bbox": bbox,
                        "reading_order": element['reading_order'],
                        "confidence": element.get('confidence', 0)
                    }
            
            elif element_type == 'table':
                # Save table as image for visual reasoning
                table_path = output_dir / "tables" / f"table_p{page_num}_{element_idx}.png"
                
                if page_image:
                    # Scale bbox to extraction DPI
                    scale = self.extraction_dpi / self.detection_dpi
                    scaled_bbox = tuple(int(coord * scale) for coord in bbox)
                    
                    # Crop and save with some padding
                    padding = 10
                    padded_bbox = (
                        max(0, scaled_bbox[0] - padding),
                        max(0, scaled_bbox[1] - padding),
                        min(page_image.width, scaled_bbox[2] + padding),
                        min(page_image.height, scaled_bbox[3] + padding)
                    )
                    
                    table_img = page_image.crop(padded_bbox)
                    table_img.save(table_path)
                    
                    return {
                        "type": "table",
                        "path": str(table_path.relative_to(output_dir)),
                        "bbox": bbox,
                        "reading_order": element['reading_order'],
                        "confidence": element.get('confidence', 0)
                    }
            
        except Exception as e:
            logger.error(f"Failed to process {element_type} element: {e}")
            return None
    
    def _create_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Create document metadata."""
        # Get basic PDF info
        page_count = 0
        with pdfplumber.open(pdf_path) as pdf:
            page_count = len(pdf.pages)
        
        return {
            "filename": pdf_path.name,
            "path": str(pdf_path),
            "pages": page_count,
            "extraction_date": datetime.now().isoformat(),
            "pipeline_version": "1.0",
            "config": {
                "detection_dpi": self.detection_dpi,
                "extraction_dpi": self.extraction_dpi,
                "chunk_size": self.chunk_size
            }
        }
    
    def _save_outputs(self, content: Dict[str, Any], output_dir: Path):
        """Save all outputs."""
        # Save main content JSON
        with open(output_dir / "content.json", "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        
        # Save per-page JSONs
        for page_data in content["pages"]:
            page_file = output_dir / "pages" / f"page_{page_data['page_num']:03d}.json"
            with open(page_file, "w", encoding="utf-8") as f:
                json.dump(page_data, f, indent=2, ensure_ascii=False)
    
    def _create_llm_packages(self, content: Dict[str, Any], output_dir: Path):
        """Create different formats for LLM consumption."""
        # 1. Create markdown version
        self._create_markdown_document(content, output_dir)
        
        # 2. Create chunks if needed
        if self._needs_chunking(content):
            self._create_chunks(content, output_dir)
        
        # 3. Create quick index
        self._create_index(content, output_dir)
    
    def _create_markdown_document(self, content: Dict[str, Any], output_dir: Path):
        """Create a markdown version of the document."""
        md_lines = []
        
        # Add metadata
        md_lines.append(f"# {content['metadata']['filename']}")
        md_lines.append(f"\n*Extracted on: {content['metadata']['extraction_date']}*")
        md_lines.append(f"\n*Pages: {content['metadata']['pages']}*")
        md_lines.append("\n---\n")
        
        # Process each page
        for page_data in content["pages"]:
            md_lines.append(f"\n## Page {page_data['page_num']}\n")
            
            # Add elements in reading order
            for element in sorted(page_data["elements"], key=lambda x: x["reading_order"]):
                if element["type"] in ["text", "title", "list"]:
                    # Add text content
                    if element["type"] == "title":
                        md_lines.append(f"\n### {element['content']}\n")
                    else:
                        md_lines.append(f"\n{element['content']}\n")
                
                elif element["type"] == "figure":
                    # Add figure reference
                    md_lines.append(f"\n![Figure]({element['path']})\n")
                
                elif element["type"] == "table":
                    # Add table reference
                    md_lines.append(f"\n![Table]({element['path']})\n")
                    md_lines.append("*[Table - see image for details]*\n")
            
            md_lines.append("\n---\n")
        
        # Save markdown
        with open(output_dir / "full_text.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
    
    def _needs_chunking(self, content: Dict[str, Any]) -> bool:
        """Check if document needs chunking."""
        # Simple heuristic: chunk if > 10 pages
        return content["metadata"]["pages"] > 10
    
    def _create_chunks(self, content: Dict[str, Any], output_dir: Path):
        """Create semantic chunks for large documents."""
        # Simple chunking by pages for now
        chunks = []
        chunk_size = 3  # pages per chunk
        
        for i in range(0, len(content["pages"]), chunk_size):
            chunk_pages = content["pages"][i:i + chunk_size]
            
            chunk = {
                "chunk_id": f"chunk_{i // chunk_size + 1:03d}",
                "page_range": [
                    chunk_pages[0]["page_num"],
                    chunk_pages[-1]["page_num"]
                ],
                "elements": [],
                "images": [],
                "tables": []
            }
            
            # Collect all elements
            for page in chunk_pages:
                for element in page["elements"]:
                    chunk["elements"].append(element)
                    
                    if element["type"] == "figure":
                        chunk["images"].append(element["path"])
                    elif element["type"] == "table":
                        chunk["tables"].append(element["path"])
            
            chunks.append(chunk)
            
            # Save chunk
            chunk_file = output_dir / "chunks" / f"{chunk['chunk_id']}.json"
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)
        
        # Save chunk index
        with open(output_dir / "chunks" / "index.json", "w", encoding="utf-8") as f:
            json.dump({
                "total_chunks": len(chunks),
                "chunk_size": chunk_size,
                "chunks": [
                    {
                        "id": c["chunk_id"],
                        "pages": c["page_range"],
                        "images": len(c["images"]),
                        "tables": len(c["tables"])
                    }
                    for c in chunks
                ]
            }, f, indent=2)
    
    def _create_index(self, content: Dict[str, Any], output_dir: Path):
        """Create a quick index of the document."""
        index = {
            "metadata": content["metadata"],
            "statistics": {
                "total_elements": sum(len(p["elements"]) for p in content["pages"]),
                "text_elements": sum(
                    1 for p in content["pages"] 
                    for e in p["elements"] 
                    if e["type"] in ["text", "title", "list"]
                ),
                "figures": sum(
                    1 for p in content["pages"] 
                    for e in p["elements"] 
                    if e["type"] == "figure"
                ),
                "tables": sum(
                    1 for p in content["pages"] 
                    for e in p["elements"] 
                    if e["type"] == "table"
                )
            },
            "page_summary": [
                {
                    "page": p["page_num"],
                    "elements": len(p["elements"]),
                    "types": {
                        t: sum(1 for e in p["elements"] if e["type"] == t)
                        for t in ["text", "title", "list", "figure", "table"]
                    }
                }
                for p in content["pages"]
            ]
        }
        
        with open(output_dir / "index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
    
    def _save_page_images(self, pdf_path: Path, output_dir: Path):
        """Save full page images."""
        logger.info("Saving full page images...")
        pages = convert_from_path(pdf_path, dpi=self.extraction_dpi)
        
        for i, page_img in enumerate(pages):
            page_path = output_dir / "pages" / f"page_{i+1:03d}.png"
            page_img.save(page_path)


def run_pipeline(pdf_path: str, output_dir: str = "output", **kwargs):
    """Convenience function to run the pipeline."""
    pipeline = CompletePDFIngestionPipeline(
        output_base_dir=output_dir,
        **kwargs
    )
    return pipeline.process_pdf(pdf_path)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        output_path = run_pipeline(
            pdf_file,
            save_page_images=True
        )
        print(f"✓ Processing complete! Output saved to: {output_path}")
    else:
        print("Usage: python complete_pipeline.py <pdf_file>")