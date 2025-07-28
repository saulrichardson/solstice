"""PDF element catalog pipeline - Complete version with weighted merging and column detection.

This pipeline:
1. Detects all elements (text, tables, figures)
2. Applies weighted box merging to consolidate related elements
3. Detects column structure and applies appropriate reading order
4. Extracts text content for text elements using pdfplumber
5. Keeps images/tables as references to be extracted on-demand
6. Creates an auditable catalog with separate stages
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
from .agent.merge_boxes_weighted import smart_merge_and_resolve
from .agent.refine_layout import Box
from .extractors.component_extractors import ComponentRouter
from .visualizers import CatalogVisualizer

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


class PDFElementCatalogComplete:
    """Creates a catalog of PDF elements with weighted merging and column detection."""
    
    def __init__(
        self,
        output_base_dir: str = "output/catalogs",
        detection_dpi: int = 200,
        save_thumbnails: bool = True,
        thumbnail_size: Tuple[int, int] = (200, 200),
        save_intermediate_stages: bool = True,
        # Weighted merging parameters
        confidence_weight: float = 0.7,
        area_weight: float = 0.3,
        overlap_threshold: float = 0.7,
        # Visualization parameters
        create_visualizations: bool = True
    ):
        """Initialize the catalog pipeline.
        
        Args:
            output_base_dir: Base directory for outputs
            detection_dpi: DPI for layout detection
            save_thumbnails: Whether to save element thumbnails
            thumbnail_size: Size for thumbnails
            save_intermediate_stages: Save outputs from each pipeline stage
            confidence_weight: Weight for confidence in merging decisions
            area_weight: Weight for box area in merging decisions
            overlap_threshold: Minimum overlap to consider merging
        """
        self.output_base = Path(output_base_dir)
        self.detection_dpi = detection_dpi
        self.save_thumbnails = save_thumbnails
        self.thumbnail_size = thumbnail_size
        self.save_intermediate_stages = save_intermediate_stages
        
        # Weighted merging parameters
        self.confidence_weight = confidence_weight
        self.area_weight = area_weight
        self.overlap_threshold = overlap_threshold
        self.create_visualizations = create_visualizations
        
        # Initialize components
        self.layout_detector = LayoutDetectionPipeline(
            model=None,
            score_threshold=0.5,
            detection_dpi=self.detection_dpi
        )
        self.component_router = ComponentRouter()
        
        # Initialize visualizer if needed
        if self.create_visualizations:
            self.visualizer = CatalogVisualizer(detection_dpi=self.detection_dpi)
    
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
            
            # 4. Weighted box merging
            logger.info("Stage 2: Applying weighted box merging...")
            merged_results = self._apply_weighted_merging(layout_results)
            if self.save_intermediate_stages:
                self._save_stage_output(merged_results, catalog_dir, "stage2_weighted_merging.json")
            
            # 5. Column detection and ordering
            logger.info("Stage 3: Detecting columns and determining reading order...")
            ordered_results = self._apply_column_aware_ordering(merged_results)
            if self.save_intermediate_stages:
                self._save_stage_output(ordered_results, catalog_dir, "stage3_column_ordering.json")
            
            # 6. Text extraction
            logger.info("Stage 4: Extracting text content...")
            results_with_text = self._extract_text_content(pdf_path, ordered_results)
            if self.save_intermediate_stages:
                self._save_stage_output(results_with_text, catalog_dir, "stage4_text_extraction.json")
            
            # 7. Create element catalog
            logger.info("Stage 5: Creating element catalog...")
            catalog = self._create_element_catalog(results_with_text, catalog_dir)
            
            # 8. Save catalog
            self._save_catalog(catalog, catalog_dir)
            
            # 9. Create thumbnails if requested
            if self.save_thumbnails:
                logger.info("Stage 6: Creating element thumbnails...")
                self._create_thumbnails(pdf_path, catalog, catalog_dir)
            
            # 10. Create summary report
            self._create_summary_report(catalog, catalog_dir)
            
            # 11. Create visualizations if requested
            if self.create_visualizations:
                logger.info("Creating visualizations...")
                self.visualizer.visualize_catalog(catalog_dir, pdf_path)
            
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
        
        # Convert to our expected format with PDF page dimensions
        results = []
        
        # Open PDF to get actual page dimensions
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, (layout, pdf_page) in enumerate(zip(layouts, pdf.pages), 1):
                # Get actual PDF page dimensions in points
                page_width = float(pdf_page.width)
                page_height = float(pdf_page.height)
                
                # Calculate scale factor from detection pixels to PDF points
                # Detection is done at detection_dpi (e.g., 200), PDF is at 72 DPI
                scale_factor = 72.0 / self.detection_dpi
                
                layout_boxes = []
                for element in layout:
                    # Extract bounding box and convert from pixels to PDF points
                    x1, y1, x2, y2 = element.coordinates
                    
                    # Convert from detection pixels to PDF points
                    pdf_x1 = float(x1) * scale_factor
                    pdf_y1 = float(y1) * scale_factor
                    pdf_x2 = float(x2) * scale_factor
                    pdf_y2 = float(y2) * scale_factor
                    
                    layout_boxes.append({
                        'type': element.type,
                        'bbox': [pdf_x1, pdf_y1, pdf_x2, pdf_y2],
                        'confidence': float(element.score) if hasattr(element, 'score') else 1.0
                    })
                
                results.append({
                    'page_num': page_num,
                    'page_width': page_width,
                    'page_height': page_height,
                    'layout_boxes': layout_boxes
                })
        
        return results
    
    def _apply_weighted_merging(self, layout_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply weighted box merging to consolidate related elements."""
        merged_results = []
        
        for page_result in layout_results:
            # Convert layout boxes to Box objects for merging
            boxes = []
            for i, box_data in enumerate(page_result['layout_boxes']):
                box = Box(
                    id=f"box_{i}",
                    label=box_data['type'],
                    bbox=tuple(box_data['bbox']),
                    score=box_data['confidence']
                )
                boxes.append(box)
            
            # Apply smart merging: first merge same-type boxes, then resolve conflicts
            merged_boxes = smart_merge_and_resolve(
                boxes,
                merge_same_type=True,
                merge_threshold=0.1,  # IoU threshold for same-type merging
                confidence_weight=self.confidence_weight,
                area_weight=self.area_weight,
                abstract_hint_area=0.1
            )
            
            # Convert back to our format
            merged_layout_boxes = []
            for box in merged_boxes:
                merged_layout_boxes.append({
                    'type': box.label,
                    'bbox': list(box.bbox),
                    'confidence': box.score,
                    'id': box.id
                })
            
            merged_results.append({
                'page_num': page_result['page_num'],
                'page_width': page_result['page_width'],
                'page_height': page_result['page_height'],
                'layout_boxes': merged_layout_boxes
            })
        
        return merged_results
    
    def _apply_column_aware_ordering(self, merged_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply column detection and determine reading order."""
        ordered_results = []
        
        for page_result in merged_results:
            page_width = page_result['page_width']
            elements = []
            
            # Convert layout boxes to elements
            for box in page_result.get('layout_boxes', []):
                elements.append({
                    'type': box['type'].lower(),
                    'bbox': box['bbox'],
                    'confidence': box['confidence'],
                    'original_box': box
                })
            
            # Detect columns and order
            ordered_elements = self._detect_and_order_columns(elements, page_width)
            
            ordered_results.append({
                'page_num': page_result['page_num'],
                'page_width': page_result['page_width'],
                'page_height': page_result['page_height'],
                'ordered_elements': ordered_elements
            })
        
        return ordered_results
    
    def _detect_and_order_columns(self, elements: List[Dict[str, Any]], page_width: float) -> List[Dict[str, Any]]:
        """Detect column structure and order elements accordingly."""
        if not elements:
            return []
        
        # Get text elements for column detection (exclude wide elements)
        text_elements = [e for e in elements if e['type'] in ['text', 'list']]
        
        if len(text_elements) < 4:
            # Not enough elements for column detection, use simple ordering
            return self._simple_top_down_ordering(elements)
        
        # Calculate element widths
        element_widths = [(e['bbox'][2] - e['bbox'][0]) for e in text_elements]
        avg_width = sum(element_widths) / len(element_widths) if element_widths else page_width / 2
        
        # Find elements that could be in columns (not too wide)
        column_candidates = [e for e in text_elements if (e['bbox'][2] - e['bbox'][0]) < page_width * 0.6]
        
        if len(column_candidates) < 4:
            return self._simple_top_down_ordering(elements)
        
        # Analyze x-positions to find columns
        x_positions = sorted([e['bbox'][0] for e in column_candidates])
        
        # Look for significant gaps that indicate column boundaries
        gaps = []
        for i in range(1, len(x_positions)):
            gap = x_positions[i] - x_positions[i-1]
            if gap > avg_width * 0.5:  # Significant gap
                gaps.append((x_positions[i-1], x_positions[i]))
        
        if not gaps:
            # No clear columns detected
            return self._simple_top_down_ordering(elements)
        
        # Check for two-column layout
        if len(gaps) == 1 and gaps[0][0] < page_width * 0.6:
            # Two-column layout detected
            return self._two_column_ordering(elements, gaps[0], page_width)
        
        # Default to simple ordering
        return self._simple_top_down_ordering(elements)
    
    def _simple_top_down_ordering(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple top-to-bottom, left-to-right ordering."""
        # Sort by y-position (top to bottom), then x-position (left to right)
        sorted_elements = sorted(elements, key=lambda e: (-e['bbox'][3], e['bbox'][0]))
        
        # Assign reading order
        for i, elem in enumerate(sorted_elements):
            elem['reading_order'] = i + 1
        
        return sorted_elements
    
    def _two_column_ordering(self, elements: List[Dict[str, Any]], gap: Tuple[float, float], page_width: float) -> List[Dict[str, Any]]:
        """Order elements for two-column layout."""
        middle = (gap[0] + gap[1]) / 2
        
        # Categorize elements
        spanning_elements = []
        left_column = []
        right_column = []
        
        for elem in elements:
            elem_center = (elem['bbox'][0] + elem['bbox'][2]) / 2
            elem_width = elem['bbox'][2] - elem['bbox'][0]
            
            # Check if element spans columns
            if elem_width > page_width * 0.6 or (elem['bbox'][0] < middle - 50 and elem['bbox'][2] > middle + 50):
                spanning_elements.append(elem)
            elif elem_center < middle:
                left_column.append(elem)
            else:
                right_column.append(elem)
        
        # Sort each group
        spanning_elements.sort(key=lambda e: -e['bbox'][3])  # Top to bottom
        left_column.sort(key=lambda e: -e['bbox'][3])  # Top to bottom
        right_column.sort(key=lambda e: -e['bbox'][3])  # Top to bottom
        
        # Combine in reading order: spanning elements first, then left column, then right column
        ordered_elements = []
        reading_order = 1
        
        # Process spanning elements at the top
        top_spanning = [e for e in spanning_elements if e['bbox'][3] > (sum(e['bbox'][3] for e in elements) / len(elements))]
        for elem in top_spanning:
            elem['reading_order'] = reading_order
            ordered_elements.append(elem)
            reading_order += 1
        
        # Process columns
        for elem in left_column:
            elem['reading_order'] = reading_order
            ordered_elements.append(elem)
            reading_order += 1
        
        for elem in right_column:
            elem['reading_order'] = reading_order
            ordered_elements.append(elem)
            reading_order += 1
        
        # Process remaining spanning elements at the bottom
        bottom_spanning = [e for e in spanning_elements if e not in top_spanning]
        for elem in bottom_spanning:
            elem['reading_order'] = reading_order
            ordered_elements.append(elem)
            reading_order += 1
        
        return ordered_elements
    
    def _extract_text_content(
        self,
        pdf_path: Path,
        ordered_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract text content for text elements."""
        results_with_text = []
        
        # Use laparams for better text extraction
        laparams = {
            "line_overlap": 0.5,
            "char_margin": 2.0,
            "word_margin": 0.1,
            "line_margin": 0.5,
            "boxes_flow": 0.5,
            "detect_vertical": False,
            "all_texts": True
        }
        
        with pdfplumber.open(pdf_path, laparams=laparams) as pdf:
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
                            
                            # Use the bbox directly - pdfplumber expects (x0, y0, x1, y1)
                            plumber_bbox = (
                                float(bbox[0]),  # x0
                                float(bbox[1]),  # y0 (bottom)
                                float(bbox[2]),  # x1
                                float(bbox[3])   # y1 (top)
                            )
                            
                            try:
                                # Crop the page to the bbox
                                cropped = pdf_page.within_bbox(plumber_bbox, relative=False)
                                
                                # Extract text with better handling
                                # Using extract_words first to get better spacing
                                words = cropped.extract_words(
                                    x_tolerance=3,
                                    y_tolerance=3,
                                    keep_blank_chars=False,
                                    use_text_flow=True,
                                    extra_attrs=['fontname', 'size']
                                )
                                
                                if words:
                                    # Group words into lines
                                    lines = []
                                    current_line = []
                                    current_y = None
                                    line_tolerance = 3
                                    
                                    for word in sorted(words, key=lambda w: (-w['top'], w['x0'])):
                                        word_y = word['top']
                                        
                                        if current_y is None or abs(word_y - current_y) <= line_tolerance:
                                            current_line.append(word)
                                            if current_y is None:
                                                current_y = word_y
                                        else:
                                            if current_line:
                                                lines.append(current_line)
                                            current_line = [word]
                                            current_y = word_y
                                    
                                    if current_line:
                                        lines.append(current_line)
                                    
                                    # Build text from words
                                    text_lines = []
                                    for line in lines:
                                        # Sort words in line by x position
                                        line.sort(key=lambda w: w['x0'])
                                        
                                        # Join words with appropriate spacing
                                        line_text = ""
                                        for i, word in enumerate(line):
                                            if i > 0:
                                                # Add space between words
                                                prev_word = line[i-1]
                                                # Check if there's enough gap for a space
                                                gap = word['x0'] - prev_word['x1']
                                                # Use font size to determine space threshold
                                                space_threshold = min(word.get('size', 12), prev_word.get('size', 12)) * 0.2
                                                if gap > space_threshold:
                                                    line_text += " "
                                            line_text += word['text']
                                        
                                        text_lines.append(line_text)
                                    
                                    # Join lines
                                    element_copy['content'] = '\n'.join(text_lines).strip()
                                else:
                                    # Fallback to simple text extraction
                                    text = cropped.extract_text()
                                    element_copy['content'] = text.strip() if text else ""
                                    
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
                "pipeline_version": "complete-weighted-columns",
                "pipeline_config": {
                    "confidence_weight": self.confidence_weight,
                    "area_weight": self.area_weight,
                    "overlap_threshold": self.overlap_threshold
                }
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
                # Convert PDF points back to pixels for image cropping
                scale_factor = self.detection_dpi / 72.0
                pixel_bbox = [
                    int(bbox[0] * scale_factor),
                    int(bbox[1] * scale_factor),
                    int(bbox[2] * scale_factor),
                    int(bbox[3] * scale_factor)
                ]
                
                # Crop element from page
                try:
                    cropped = current_image.crop(pixel_bbox)
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
        report.append(f"\n## Pipeline Configuration\n")
        report.append(f"- Confidence weight: {catalog['metadata']['pipeline_config']['confidence_weight']}\n")
        report.append(f"- Area weight: {catalog['metadata']['pipeline_config']['area_weight']}\n")
        report.append(f"- Overlap threshold: {catalog['metadata']['pipeline_config']['overlap_threshold']}\n")
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


def create_catalog_complete(
    pdf_path: str | Path,
    catalog_name: Optional[str] = None,
    output_dir: str = "output/catalogs",
    **kwargs
) -> Path:
    """Convenience function to create a complete catalog with weighted merging and column detection.
    
    Args:
        pdf_path: Path to PDF file
        catalog_name: Optional name for catalog
        output_dir: Output directory for catalogs
        **kwargs: Additional parameters for PDFElementCatalogComplete
        
    Returns:
        Path to created catalog directory
    """
    cataloger = PDFElementCatalogComplete(output_base_dir=output_dir, **kwargs)
    return cataloger.create_catalog(pdf_path, catalog_name)