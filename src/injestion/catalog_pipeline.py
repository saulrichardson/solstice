"""PDF element catalog pipeline - creates an index without extracting everything.

This pipeline:
1. Detects all elements (text, tables, figures)
2. Creates a catalog/index of what's available
3. Provides on-demand extraction utilities
4. Lets downstream agents decide what to process
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
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.metadata is None:
            data.pop('metadata')
        return data


class PDFElementCatalog:
    """Creates a catalog of PDF elements without extracting content."""
    
    def __init__(
        self,
        output_base_dir: str = "output",
        detection_dpi: int = 200,
        save_thumbnails: bool = True,
        thumbnail_size: Tuple[int, int] = (200, 200)
    ):
        """Initialize the catalog pipeline.
        
        Args:
            output_base_dir: Base directory for outputs
            detection_dpi: DPI for layout detection
            save_thumbnails: Whether to save element thumbnails
            thumbnail_size: Size for thumbnails
        """
        self.output_base = Path(output_base_dir)
        self.detection_dpi = detection_dpi
        self.save_thumbnails = save_thumbnails
        self.thumbnail_size = thumbnail_size
        
        # Initialize components
        self.layout_detector = LayoutDetectionPipeline(
            model=None,
            score_threshold=0.5,
            detection_dpi=self.detection_dpi
        )
        self.reordering_agent = VisualReorderingAgent()
    
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
        """Create element catalog for PDF.
        
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
            logger.info("Detecting layout elements...")
            layout_results = self._detect_layout(pdf_path)
            
            # 4. Visual reordering
            logger.info("Applying visual reordering...")
            ordered_results = self._apply_visual_reordering(layout_results)
            
            # 5. Create element catalog
            logger.info("Creating element catalog...")
            catalog = self._create_element_catalog(ordered_results, catalog_dir)
            
            # 6. Save catalog
            self._save_catalog(catalog, catalog_dir)
            
            # 7. Create thumbnails if requested
            if self.save_thumbnails:
                logger.info("Creating element thumbnails...")
                self._create_thumbnails(pdf_path, catalog, catalog_dir)
            
            logger.info(f"✓ Catalog created! {len(catalog['elements'])} elements found")
            return catalog_dir
            
        except Exception as e:
            logger.error(f"Catalog creation failed: {e}")
            raise
    
    def _setup_directories(self, catalog_dir: Path):
        """Create catalog directory structure."""
        catalog_dir.mkdir(parents=True, exist_ok=True)
        (catalog_dir / "thumbnails").mkdir(exist_ok=True)
        (catalog_dir / "extracts").mkdir(exist_ok=True)  # For on-demand extraction
    
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
    
    def _create_element_catalog(
        self,
        ordered_results: List[Dict[str, Any]],
        catalog_dir: Path
    ) -> Dict[str, Any]:
        """Create catalog of all elements."""
        catalog = {
            "metadata": {
                "created": datetime.now().isoformat(),
                "detection_dpi": self.detection_dpi,
                "total_pages": len(ordered_results),
                "pipeline_version": "2.0"
            },
            "pages": {},
            "elements": [],
            "statistics": {
                "total_elements": 0,
                "by_type": {},
                "by_page": {}
            }
        }
        
        element_counter = 0
        
        for page_data in ordered_results:
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
                    reading_order=element['reading_order']
                )
                
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
            
            if current_image and current_page == page_num:
                # Create thumbnail
                bbox = element['bbox']
                cropped = current_image.crop(tuple(map(int, bbox)))
                
                # Resize to thumbnail size
                cropped.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumb_path = catalog_dir / "thumbnails" / f"{element['element_id']}.png"
                cropped.save(thumb_path)


class OnDemandExtractor:
    """Extract content on-demand from catalog."""
    
    def __init__(self, catalog_dir: Path):
        """Initialize with catalog directory."""
        self.catalog_dir = Path(catalog_dir)
        self.extractor = ComponentRouter()
        
        # Load catalog
        with open(self.catalog_dir / "catalog.json") as f:
            self.catalog = json.load(f)
        
        # Load PDF reference
        with open(self.catalog_dir / "pdf_reference.json") as f:
            pdf_ref = json.load(f)
            self.pdf_path = Path(pdf_ref['original_path'])
    
    def get_element(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get element metadata by ID."""
        for elem in self.catalog['elements']:
            if elem['element_id'] == element_id:
                return elem
        return None
    
    def extract_element(
        self,
        element_id: str,
        extraction_dpi: Optional[int] = None
    ) -> Dict[str, Any]:
        """Extract content for a specific element.
        
        Args:
            element_id: Element ID from catalog
            extraction_dpi: DPI for extraction (default: detection DPI)
            
        Returns:
            Extracted content based on element type
        """
        # Get element metadata
        element = self.get_element(element_id)
        if not element:
            raise ValueError(f"Element not found: {element_id}")
        
        # Check if already extracted
        extract_path = self.catalog_dir / "extracts" / f"{element_id}.json"
        if extract_path.exists():
            with open(extract_path) as f:
                return json.load(f)
        
        # Extract based on type
        detection_dpi = self.catalog['metadata']['detection_dpi']
        
        if element['element_type'] in ['text', 'title', 'list']:
            # Extract text
            result = self.extractor.extract_component(
                element['element_type'],
                self.pdf_path,
                element['page_num'],
                element['bbox'],
                detection_dpi=detection_dpi
            )
            
            extracted = {
                "element_id": element_id,
                "type": element['element_type'],
                "content": result.get('text', ''),
                "extracted_at": datetime.now().isoformat()
            }
        
        elif element['element_type'] in ['figure', 'table']:
            # Extract as image
            if extraction_dpi is None:
                extraction_dpi = detection_dpi
            
            # Convert page to image
            images = convert_from_path(
                self.pdf_path,
                first_page=element['page_num'],
                last_page=element['page_num'],
                dpi=extraction_dpi
            )
            
            if images:
                # Scale bbox
                scale = extraction_dpi / detection_dpi
                scaled_bbox = tuple(int(coord * scale) for coord in element['bbox'])
                
                # Crop and save
                image = images[0].crop(scaled_bbox)
                image_path = self.catalog_dir / "extracts" / f"{element_id}.png"
                image.save(image_path)
                
                extracted = {
                    "element_id": element_id,
                    "type": element['element_type'],
                    "image_path": str(image_path),
                    "extracted_at": datetime.now().isoformat()
                }
            else:
                extracted = {"error": "Failed to convert page"}
        
        else:
            extracted = {"error": f"Unknown element type: {element['element_type']}"}
        
        # Save extraction result
        with open(extract_path, "w") as f:
            json.dump(extracted, f, indent=2)
        
        return extracted
    
    def extract_multiple(
        self,
        element_ids: List[str],
        extraction_dpi: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Extract multiple elements."""
        results = {}
        for elem_id in element_ids:
            try:
                results[elem_id] = self.extract_element(elem_id, extraction_dpi)
            except Exception as e:
                results[elem_id] = {"error": str(e)}
        return results
    
    def get_elements_by_type(self, element_type: str) -> List[Dict[str, Any]]:
        """Get all elements of a specific type."""
        return [
            elem for elem in self.catalog['elements']
            if elem['element_type'] == element_type
        ]
    
    def get_page_elements(self, page_num: int) -> List[Dict[str, Any]]:
        """Get all elements on a specific page."""
        return [
            elem for elem in self.catalog['elements']
            if elem['page_num'] == page_num
        ]


# Example agent interface
class SelectiveExtractionAgent:
    """Example agent that selectively extracts content."""
    
    def __init__(self, catalog_dir: Path):
        self.extractor = OnDemandExtractor(catalog_dir)
    
    def process_document(self, task: str) -> Dict[str, Any]:
        """Process document based on task."""
        
        if task == "extract_all_titles":
            # Get all title elements
            titles = self.extractor.get_elements_by_type('title')
            results = []
            
            for title in titles:
                extracted = self.extractor.extract_element(title['element_id'])
                results.append({
                    "page": title['page_num'],
                    "content": extracted.get('content', ''),
                    "order": title['reading_order']
                })
            
            return {"titles": results}
        
        elif task == "get_first_table":
            # Find first table
            tables = self.extractor.get_elements_by_type('table')
            if tables:
                # Sort by page and reading order
                first_table = sorted(
                    tables,
                    key=lambda x: (x['page_num'], x['reading_order'])
                )[0]
                
                return self.extractor.extract_element(first_table['element_id'])
        
        elif task == "extract_page_1":
            # Get all elements from page 1
            page_elements = self.extractor.get_page_elements(1)
            results = []
            
            for elem in sorted(page_elements, key=lambda x: x['reading_order']):
                extracted = self.extractor.extract_element(elem['element_id'])
                results.append(extracted)
            
            return {"page_1": results}
        
        return {"error": f"Unknown task: {task}"}


def create_catalog(pdf_path: str, output_dir: str = "catalogs", **kwargs):
    """Convenience function to create catalog."""
    cataloger = PDFElementCatalog(output_base_dir=output_dir, **kwargs)
    return cataloger.create_catalog(pdf_path)