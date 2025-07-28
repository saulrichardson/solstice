"""PDF element catalog pipeline V2 - includes text extraction during catalog creation.

This pipeline:
1. Detects all elements (text, tables, figures)
2. Extracts text content for text elements during catalog creation
3. Keeps images/tables as references to be extracted on-demand
4. Creates an auditable catalog with separate stages
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image
from pdf2image import convert_from_path
import pdfplumber

from .layout_pipeline import LayoutDetectionPipeline
from .agent.visual_reordering_agent import VisualReorderingAgent
from .extractors.component_extractors import ComponentRouter

logger = logging.getLogger(__name__)


@dataclass
class DocumentElement:
    """Represents a single element in the document."""
    element_id: str
    page_num: int
    element_type: str  # text, figure, table, title, list
    bbox: Tuple[float, float, float, float]
    confidence: float
    reading_order: int
    content: Optional[str] = None  # For text elements
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.metadata is None:
            data.pop('metadata')
        if self.content is None:
            data.pop('content')
        return data


class PDFElementCatalogV2:
    """Creates a catalog of PDF elements with text pre-extracted."""
    
    def __init__(
        self,
        output_base_dir: str = "output/catalogs",
        detection_dpi: int = 200,
        save_thumbnails: bool = True,
        thumbnail_size: Tuple[int, int] = (200, 200),
        save_intermediate_stages: bool = True
    ):
        """Initialize the catalog pipeline.
        
        Args:
            output_base_dir: Base directory for outputs
            detection_dpi: DPI for layout detection
            save_thumbnails: Whether to save element thumbnails
            thumbnail_size: Size for thumbnails
            save_intermediate_stages: Save outputs from each pipeline stage
        """
        self.output_base = Path(output_base_dir)
        self.detection_dpi = detection_dpi
        self.save_thumbnails = save_thumbnails
        self.thumbnail_size = thumbnail_size
        self.save_intermediate_stages = save_intermediate_stages
        
        # Initialize components
        self.layout_detector = LayoutDetectionPipeline(
            model=None,
            score_threshold=0.5,
            detection_dpi=self.detection_dpi
        )
        self.reordering_agent = VisualReorderingAgent()
        self.component_router = ComponentRouter()
    
    def _cuda_available(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def create_catalog(
        self,
        pdf_path: str | Path,
        catalog_name: Optional[str] = None
    ) -> Path:
        """Create element catalog for PDF with text extraction.
        
        Args:
            pdf_path: Path to PDF file
            catalog_name: Optional name for catalog directory
            
        Returns:
            Path to catalog directory
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Setup output directory
        if catalog_name is None:
            catalog_name = pdf_path.stem
        catalog_dir = self.output_base / catalog_name
        
        logger.info(f"Creating catalog for: {pdf_path}")
        logger.info(f"Catalog directory: {catalog_dir}")
        
        try:
            # 1. Setup directories
            self._setup_directories(catalog_dir)
            
            # 2. Save PDF reference
            self._save_pdf_reference(pdf_path, catalog_dir)
            
            # 3. Layout detection
            logger.info("Stage 1: Detecting layout elements...")
            layout_results = self._detect_layout(pdf_path)
            if self.save_intermediate_stages:
                self._save_stage_output(layout_results, catalog_dir, "stage1_layout_detection.json")
            
            # 4. Visual reordering
            logger.info("Stage 2: Applying visual reordering...")
            ordered_results = self._apply_visual_reordering(layout_results)
            if self.save_intermediate_stages:
                self._save_stage_output(ordered_results, catalog_dir, "stage2_visual_reordering.json")
            
            # 5. Text extraction
            logger.info("Stage 3: Extracting text content...")
            results_with_text = self._extract_text_content(pdf_path, ordered_results)
            if self.save_intermediate_stages:
                self._save_stage_output(results_with_text, catalog_dir, "stage3_text_extraction.json")
            
            # 6. Create element catalog
            logger.info("Stage 4: Creating element catalog...")
            catalog = self._create_element_catalog(results_with_text, catalog_dir)
            
            # 7. Save catalog
            self._save_catalog(catalog, catalog_dir)
            
            # 8. Create thumbnails if requested
            if self.save_thumbnails:
                logger.info("Stage 5: Creating element thumbnails...")
                self._create_thumbnails(pdf_path, catalog, catalog_dir)
            
            # 9. Create summary report
            self._create_summary_report(catalog, catalog_dir)
            
            logger.info(f"✓ Catalog created! {len(catalog['elements'])} elements found")
            logger.info(f"  - Text elements extracted: {catalog['statistics']['text_extracted']}")
            logger.info(f"  - Image/table references: {catalog['statistics']['image_references']}")
            
            return catalog_dir
            
        except Exception as e:
            logger.error(f"Catalog creation failed: {e}")
            raise
    
    def _setup_directories(self, catalog_dir: Path):
        """Create catalog directory structure."""
        catalog_dir.mkdir(parents=True, exist_ok=True)
        (catalog_dir / "stages").mkdir(exist_ok=True)  # For intermediate outputs
        (catalog_dir / "thumbnails").mkdir(exist_ok=True)
        (catalog_dir / "extracts").mkdir(exist_ok=True)  # For on-demand extraction
        (catalog_dir / "text_content").mkdir(exist_ok=True)  # For extracted text
    
    def _save_pdf_reference(self, pdf_path: Path, catalog_dir: Path):
        """Save reference to original PDF."""
        ref_data = {
            "original_path": str(pdf_path.absolute()),
            "filename": pdf_path.name,
            "size_bytes": pdf_path.stat().st_size,
            "catalog_created": datetime.now().isoformat()
        }
        
        with open(catalog_dir / "pdf_reference.json", "w") as f:
            json.dump(ref_data, f, indent=2)
    
    def _save_stage_output(self, data: Any, catalog_dir: Path, filename: str):
        """Save intermediate stage output for auditing."""
        with open(catalog_dir / "stages" / filename, "w") as f:
            json.dump(data, f, indent=2)
    
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
            elements = []
            
            # Convert layout boxes to elements
            for box in page_result.get('layout_boxes', []):
                elements.append({
                    'type': box['type'].lower(),
                    'bbox': box['bbox'],
                    'confidence': box['confidence'],
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
                'ordered_elements': ordered_elements
            })
        
        return ordered_results
    
    def _extract_text_content(
        self,
        pdf_path: Path,
        ordered_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract text content for text elements."""
        results_with_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_data in ordered_results:
                page_num = page_data['page_num']
                
                # Get the PDF page
                if page_num <= len(pdf.pages):
                    pdf_page = pdf.pages[page_num - 1]
                    
                    # Process each element
                    elements_with_text = []
                    for element in page_data['ordered_elements']:
                        element_copy = element.copy()
                        
                        # Extract text for text-based elements
                        if element['type'] in ['text', 'title', 'list']:
                            bbox = element['bbox']
                            
                            # Convert bbox to pdfplumber format (x0, top, x1, bottom)
                            # Note: pdfplumber uses top-origin, layout detection uses bottom-origin
                            page_height = float(pdf_page.height)
                            plumber_bbox = (
                                float(bbox[0]),  # x0
                                page_height - float(bbox[3]),  # top (flip y)
                                float(bbox[2]),  # x1
                                page_height - float(bbox[1])   # bottom (flip y)
                            )
                            
                            try:
                                # Crop the page to the bbox
                                cropped = pdf_page.within_bbox(plumber_bbox)
                                text = cropped.extract_text()
                                
                                if text:
                                    element_copy['content'] = text.strip()
                                else:
                                    element_copy['content'] = ""
                                    
                            except Exception as e:
                                logger.warning(f"Failed to extract text from bbox {bbox}: {e}")
                                element_copy['content'] = ""
                        
                        elements_with_text.append(element_copy)
                    
                    page_data_copy = page_data.copy()
                    page_data_copy['ordered_elements'] = elements_with_text
                    results_with_text.append(page_data_copy)
                    
                else:
                    logger.warning(f"Page {page_num} not found in PDF")
                    results_with_text.append(page_data)
        
        return results_with_text
    
    def _create_element_catalog(
        self,
        results_with_text: List[Dict[str, Any]],
        catalog_dir: Path
    ) -> Dict[str, Any]:
        """Create catalog of all elements with extracted text."""
        catalog = {
            "metadata": {
                "created": datetime.now().isoformat(),
                "detection_dpi": self.detection_dpi,
                "total_pages": len(results_with_text),
                "pipeline_version": "2.0-with-text"
            },
            "pages": {},
            "elements": [],
            "statistics": {
                "total_elements": 0,
                "text_extracted": 0,
                "image_references": 0,
                "by_type": {},
                "by_page": {}
            }
        }
        
        element_counter = 0
        
        for page_data in results_with_text:
            page_num = page_data['page_num']
            page_info = {
                "width": page_data['page_width'],
                "height": page_data['page_height'],
                "element_ids": []
            }
            
            page_element_count = 0
            
            for element in page_data['ordered_elements']:
                element_counter += 1
                element_id = f"elem_{page_num:03d}_{element_counter:04d}"
                
                # Create element entry
                doc_element = DocumentElement(
                    element_id=element_id,
                    page_num=page_num,
                    element_type=element['type'],
                    bbox=element['bbox'],
                    confidence=element.get('confidence', 0),
                    reading_order=element['reading_order'],
                    content=element.get('content')  # Include extracted text
                )
                
                # Save text content to separate file for text elements
                if element.get('content'):
                    text_file = catalog_dir / "text_content" / f"{element_id}.txt"
                    with open(text_file, "w", encoding='utf-8') as f:
                        f.write(element['content'])
                    catalog['statistics']['text_extracted'] += 1
                elif element['type'] in ['figure', 'table']:
                    catalog['statistics']['image_references'] += 1
                
                catalog['elements'].append(doc_element.to_dict())
                page_info['element_ids'].append(element_id)
                page_element_count += 1
                
                # Update statistics
                elem_type = element['type']
                catalog['statistics']['by_type'][elem_type] = \
                    catalog['statistics']['by_type'].get(elem_type, 0) + 1
            
            catalog['pages'][str(page_num)] = page_info
            catalog['statistics']['by_page'][str(page_num)] = page_element_count
        
        catalog['statistics']['total_elements'] = element_counter
        
        return catalog
    
    def _save_catalog(self, catalog: Dict[str, Any], catalog_dir: Path):
        """Save catalog to disk."""
        # Save main catalog
        with open(catalog_dir / "catalog.json", "w") as f:
            json.dump(catalog, f, indent=2)
        
        # Save element list for quick access
        with open(catalog_dir / "elements.json", "w") as f:
            json.dump(catalog['elements'], f, indent=2)
        
        # Save index by type
        by_type = {}
        for elem in catalog['elements']:
            elem_type = elem['element_type']
            if elem_type not in by_type:
                by_type[elem_type] = []
            by_type[elem_type].append(elem['element_id'])
        
        with open(catalog_dir / "index_by_type.json", "w") as f:
            json.dump(by_type, f, indent=2)
        
        # Save text-only elements
        text_elements = [
            elem for elem in catalog['elements']
            if elem.get('content') is not None
        ]
        with open(catalog_dir / "text_elements.json", "w") as f:
            json.dump(text_elements, f, indent=2)
    
    def _create_thumbnails(
        self,
        pdf_path: Path,
        catalog: Dict[str, Any],
        catalog_dir: Path
    ):
        """Create thumbnails for visual preview."""
        # Convert pages to images
        page_images = {}
        current_page = None
        current_image = None
        
        for element in catalog['elements']:
            page_num = element['page_num']
            
            # Load page image if not cached
            if page_num != current_page:
                if current_page is None or page_num > current_page:
                    # Convert single page
                    images = convert_from_path(
                        pdf_path,
                        first_page=page_num,
                        last_page=page_num,
                        dpi=self.detection_dpi
                    )
                    if images:
                        current_image = images[0]
                        current_page = page_num
            
            # Create thumbnail
            if current_image:
                bbox = element['bbox']
                # Crop element from page
                try:
                    cropped = current_image.crop(bbox)
                    # Resize to thumbnail size
                    cropped.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                    # Save
                    thumb_path = catalog_dir / "thumbnails" / f"{element['element_id']}.png"
                    cropped.save(thumb_path)
                except Exception as e:
                    logger.warning(f"Failed to create thumbnail for {element['element_id']}: {e}")
    
    def _create_summary_report(self, catalog: Dict[str, Any], catalog_dir: Path):
        """Create human-readable summary report."""
        report = []
        report.append(f"# PDF Catalog Summary\n")
        report.append(f"Created: {catalog['metadata']['created']}\n")
        report.append(f"Total Pages: {catalog['metadata']['total_pages']}\n")
        report.append(f"Total Elements: {catalog['statistics']['total_elements']}\n")
        report.append(f"\n## Statistics\n")
        report.append(f"- Text elements extracted: {catalog['statistics']['text_extracted']}\n")
        report.append(f"- Image/table references: {catalog['statistics']['image_references']}\n")
        report.append(f"\n## Element Types\n")
        
        for elem_type, count in sorted(catalog['statistics']['by_type'].items()):
            report.append(f"- {elem_type}: {count}\n")
        
        report.append(f"\n## Elements by Page\n")
        for page_num, count in sorted(catalog['statistics']['by_page'].items()):
            report.append(f"- Page {page_num}: {count} elements\n")
        
        # Save report
        with open(catalog_dir / "summary_report.md", "w") as f:
            f.writelines(report)


def create_catalog_v2(
    pdf_path: str | Path,
    catalog_name: Optional[str] = None,
    output_dir: str = "output/catalogs"
) -> Path:
    """Convenience function to create a catalog with text extraction.
    
    Args:
        pdf_path: Path to PDF file
        catalog_name: Optional name for catalog
        output_dir: Output directory for catalogs
        
    Returns:
        Path to created catalog directory
    """
    cataloger = PDFElementCatalogV2(output_base_dir=output_dir)
    return cataloger.create_catalog(pdf_path, catalog_name)