"""Visualizer for PDF element catalogs with bounding boxes and reading order."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)


class CatalogVisualizer:
    """Visualizes PDF catalogs with bounding boxes and reading order."""
    
    # Color scheme for element types
    ELEMENT_COLORS = {
        'text': '#3498db',      # Blue
        'title': '#e74c3c',     # Red
        'list': '#9b59b6',      # Purple
        'figure': '#2ecc71',    # Green
        'table': '#f39c12',     # Orange
    }
    
    def __init__(
        self,
        detection_dpi: int = 200,
        font_path: Optional[str] = None
    ):
        """Initialize visualizer.
        
        Args:
            detection_dpi: DPI used for detection (must match catalog)
            font_path: Optional path to font file
        """
        self.detection_dpi = detection_dpi
        self.scale_factor = detection_dpi / 72.0  # PDF points to pixels
        
        # Load fonts
        self._load_fonts(font_path)
    
    def _load_fonts(self, font_path: Optional[str] = None):
        """Load fonts for visualization."""
        try:
            if font_path:
                self.font = ImageFont.truetype(font_path, 16)
                self.title_font = ImageFont.truetype(font_path, 24)
                self.order_font = ImageFont.truetype(font_path, 32)
            else:
                # Try system fonts
                for font in ["/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
                    try:
                        self.font = ImageFont.truetype(font, 16)
                        self.title_font = ImageFont.truetype(font, 24)
                        self.order_font = ImageFont.truetype(font, 32)
                        break
                    except:
                        continue
        except:
            # Fallback to default
            self.font = ImageFont.load_default()
            self.title_font = self.font
            self.order_font = self.font
    
    def visualize_catalog(
        self,
        catalog_dir: Path,
        pdf_path: Path,
        output_dir: Optional[Path] = None,
        pages: Optional[List[int]] = None
    ) -> Path:
        """Create visualizations for a catalog.
        
        Args:
            catalog_dir: Directory containing the catalog
            pdf_path: Path to original PDF
            output_dir: Output directory (defaults to catalog_dir/visualizations)
            pages: Specific pages to visualize (None = all)
            
        Returns:
            Path to visualization directory
        """
        # Setup output directory
        if output_dir is None:
            output_dir = catalog_dir / "visualizations"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load catalog data
        with open(catalog_dir / "catalog.json") as f:
            catalog = json.load(f)
        
        # Load stage data if available
        stages_data = self._load_stage_data(catalog_dir)
        
        # Determine pages to process
        total_pages = catalog['metadata']['total_pages']
        if pages is None:
            pages = list(range(1, total_pages + 1))
        
        logger.info(f"Creating visualizations for {len(pages)} pages...")
        
        # Process each page
        for page_num in pages:
            self._visualize_page(
                page_num,
                pdf_path,
                catalog,
                stages_data,
                output_dir
            )
        
        # Create summary visualization
        self._create_summary(catalog, stages_data, output_dir)
        
        logger.info(f"✓ Visualizations saved to: {output_dir}")
        return output_dir
    
    def _load_stage_data(self, catalog_dir: Path) -> Dict[str, Any]:
        """Load intermediate stage data if available."""
        stages_data = {}
        stages_dir = catalog_dir / "stages"
        
        if stages_dir.exists():
            stage_files = {
                'stage1': 'stage1_layout_detection.json',
                'stage2': 'stage2_weighted_merging.json',
                'stage3': 'stage3_column_ordering.json'
            }
            
            for stage_key, filename in stage_files.items():
                stage_path = stages_dir / filename
                if stage_path.exists():
                    with open(stage_path) as f:
                        stages_data[stage_key] = json.load(f)
        
        return stages_data
    
    def _visualize_page(
        self,
        page_num: int,
        pdf_path: Path,
        catalog: Dict[str, Any],
        stages_data: Dict[str, Any],
        output_dir: Path
    ):
        """Visualize a single page."""
        logger.info(f"Processing page {page_num}...")
        
        # Convert PDF page to image
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=self.detection_dpi
        )
        
        if not images:
            logger.warning(f"Could not convert page {page_num}")
            return
        
        page_image = images[0]
        
        # Create visualizations for each stage if data available
        if 'stage1' in stages_data:
            self._visualize_detection_stage(
                page_image.copy(),
                stages_data['stage1'][page_num - 1],
                output_dir / f"page_{page_num:02d}_stage1_detection.png",
                "Stage 1: Initial Detection"
            )
        
        if 'stage2' in stages_data:
            self._visualize_detection_stage(
                page_image.copy(),
                stages_data['stage2'][page_num - 1],
                output_dir / f"page_{page_num:02d}_stage2_merged.png",
                "Stage 2: After Weighted Merging"
            )
        
        if 'stage3' in stages_data:
            self._visualize_final_stage(
                page_image.copy(),
                stages_data['stage3'][page_num - 1],
                output_dir / f"page_{page_num:02d}_stage3_final.png",
                "Stage 3: Final with Reading Order"
            )
        
        # Always create final visualization from catalog
        self._visualize_catalog_elements(
            page_image.copy(),
            catalog,
            page_num,
            output_dir / f"page_{page_num:02d}_catalog.png",
            "Final Catalog Elements"
        )
    
    def _visualize_detection_stage(
        self,
        image: Image.Image,
        stage_data: Dict[str, Any],
        output_path: Path,
        title: str
    ):
        """Visualize a detection stage."""
        draw = ImageDraw.Draw(image)
        
        # Draw title
        draw.text((10, 10), title, fill='black', font=self.title_font)
        
        # Get boxes
        boxes = stage_data.get('layout_boxes', [])
        
        # Draw each box
        for box in boxes:
            self._draw_box(draw, box, show_order=False)
        
        # Add statistics
        count_text = f"Total boxes: {len(boxes)}"
        draw.text((10, 40), count_text, fill='black', font=self.font)
        
        image.save(output_path)
    
    def _visualize_final_stage(
        self,
        image: Image.Image,
        stage_data: Dict[str, Any],
        output_path: Path,
        title: str
    ):
        """Visualize final stage with reading order."""
        draw = ImageDraw.Draw(image)
        
        # Draw title
        draw.text((10, 10), title, fill='black', font=self.title_font)
        
        # Get ordered elements
        elements = stage_data.get('ordered_elements', [])
        
        # Draw each element with reading order
        for elem in elements:
            self._draw_element_with_order(draw, elem)
        
        # Add statistics
        count_text = f"Total elements: {len(elements)}"
        draw.text((10, 40), count_text, fill='black', font=self.font)
        
        # Add legend
        self._draw_legend(draw, image.size)
        
        image.save(output_path)
    
    def _visualize_catalog_elements(
        self,
        image: Image.Image,
        catalog: Dict[str, Any],
        page_num: int,
        output_path: Path,
        title: str
    ):
        """Visualize elements from final catalog."""
        draw = ImageDraw.Draw(image)
        
        # Draw title
        draw.text((10, 10), title, fill='black', font=self.title_font)
        
        # Get elements for this page
        page_elements = [
            e for e in catalog['elements']
            if e['page_num'] == page_num
        ]
        
        # Sort by reading order
        page_elements.sort(key=lambda x: x['reading_order'])
        
        # Draw each element
        for elem in page_elements:
            self._draw_catalog_element(draw, elem)
        
        # Add statistics
        stats_text = []
        stats_text.append(f"Total elements: {len(page_elements)}")
        
        text_count = sum(1 for e in page_elements if e.get('content'))
        if text_count > 0:
            stats_text.append(f"Text extracted: {text_count}")
        
        y_offset = 40
        for text in stats_text:
            draw.text((10, y_offset), text, fill='black', font=self.font)
            y_offset += 25
        
        image.save(output_path)
    
    def _draw_box(self, draw: ImageDraw.Draw, box: Dict[str, Any], show_order: bool = False):
        """Draw a single bounding box."""
        # Convert coordinates
        bbox = box['bbox']
        pixel_bbox = [
            int(bbox[0] * self.scale_factor),
            int(bbox[1] * self.scale_factor),
            int(bbox[2] * self.scale_factor),
            int(bbox[3] * self.scale_factor)
        ]
        
        # Get color
        color = self.ELEMENT_COLORS.get(box['type'], '#95a5a6')
        
        # Draw rectangle
        draw.rectangle(pixel_bbox, outline=color, width=2)
        
        # Draw label
        label = box['type']
        if show_order and 'reading_order' in box:
            label = f"{box['reading_order']}: {label}"
        
        self._draw_label(draw, pixel_bbox, label, color)
    
    def _draw_element_with_order(self, draw: ImageDraw.Draw, element: Dict[str, Any]):
        """Draw element with prominent reading order."""
        # Convert coordinates
        bbox = element['bbox']
        pixel_bbox = [
            int(bbox[0] * self.scale_factor),
            int(bbox[1] * self.scale_factor),
            int(bbox[2] * self.scale_factor),
            int(bbox[3] * self.scale_factor)
        ]
        
        # Get color
        color = self.ELEMENT_COLORS.get(element['type'], '#95a5a6')
        
        # Draw rectangle
        draw.rectangle(pixel_bbox, outline=color, width=3)
        
        # Draw reading order number
        if 'reading_order' in element:
            self._draw_order_number(draw, pixel_bbox, str(element['reading_order']), color)
        
        # Draw type label
        self._draw_label(draw, pixel_bbox, element['type'], color)
    
    def _draw_catalog_element(self, draw: ImageDraw.Draw, element: Dict[str, Any]):
        """Draw element from catalog."""
        # Similar to _draw_element_with_order but handles catalog format
        bbox = element['bbox']
        pixel_bbox = [
            int(bbox[0] * self.scale_factor),
            int(bbox[1] * self.scale_factor),
            int(bbox[2] * self.scale_factor),
            int(bbox[3] * self.scale_factor)
        ]
        
        color = self.ELEMENT_COLORS.get(element['element_type'], '#95a5a6')
        
        # Different line style for text vs non-text
        width = 3 if element.get('content') else 2
        draw.rectangle(pixel_bbox, outline=color, width=width)
        
        # Draw order and label
        self._draw_order_number(draw, pixel_bbox, str(element['reading_order']), color)
        self._draw_label(draw, pixel_bbox, element['element_type'], color)
    
    def _draw_order_number(self, draw: ImageDraw.Draw, bbox: List[int], order_num: str, color: str):
        """Draw reading order number in center of bbox."""
        # Calculate center
        center_x = (bbox[0] + bbox[2]) // 2
        center_y = (bbox[1] + bbox[3]) // 2
        
        # Get text size
        text_bbox = draw.textbbox((0, 0), order_num, font=self.order_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Draw white circle background
        circle_radius = max(text_width, text_height) // 2 + 8
        draw.ellipse(
            [center_x - circle_radius, center_y - circle_radius,
             center_x + circle_radius, center_y + circle_radius],
            fill='white',
            outline=color,
            width=3
        )
        
        # Draw number
        draw.text(
            (center_x - text_width // 2, center_y - text_height // 2),
            order_num,
            fill=color,
            font=self.order_font
        )
    
    def _draw_label(self, draw: ImageDraw.Draw, bbox: List[int], label: str, color: str):
        """Draw label for element."""
        # Get text size
        text_bbox = draw.textbbox((0, 0), label, font=self.font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position at top-left of bbox
        label_x = bbox[0] + 2
        label_y = bbox[1] + 2
        
        # Draw background
        draw.rectangle(
            [label_x, label_y, label_x + text_width + 4, label_y + text_height + 4],
            fill='white',
            outline=color
        )
        
        # Draw text
        draw.text((label_x + 2, label_y + 2), label, fill=color, font=self.font)
    
    def _draw_legend(self, draw: ImageDraw.Draw, image_size: Tuple[int, int]):
        """Draw legend for element types."""
        width, height = image_size
        legend_y = height - 120
        legend_x = 10
        
        draw.text((legend_x, legend_y), "Element Types:", fill='black', font=self.font)
        
        for i, (elem_type, color) in enumerate(self.ELEMENT_COLORS.items()):
            y_offset = legend_y + 25 + (i * 20)
            # Color box
            draw.rectangle([legend_x, y_offset, legend_x + 15, y_offset + 15], fill=color)
            # Label
            draw.text((legend_x + 20, y_offset), elem_type.capitalize(), fill='black', font=self.font)
    
    def _create_summary(self, catalog: Dict[str, Any], stages_data: Dict[str, Any], output_dir: Path):
        """Create summary visualization."""
        # Create summary image
        img = Image.new('RGB', (1000, 600), 'white')
        draw = ImageDraw.Draw(img)
        
        # Title
        draw.text((20, 20), "PDF Catalog Pipeline Summary", fill='black', font=self.title_font)
        
        # Pipeline configuration
        y = 80
        if 'pipeline_config' in catalog['metadata']:
            draw.text((20, y), "Pipeline Configuration:", fill='black', font=self.title_font)
            y += 35
            
            config = catalog['metadata']['pipeline_config']
            for key, value in config.items():
                draw.text((40, y), f"• {key.replace('_', ' ').title()}: {value}", fill='black', font=self.font)
                y += 25
            y += 15
        
        # Statistics
        draw.text((20, y), "Document Statistics:", fill='black', font=self.title_font)
        y += 35
        
        stats = catalog['statistics']
        draw.text((40, y), f"• Total pages: {catalog['metadata']['total_pages']}", fill='black', font=self.font)
        y += 25
        draw.text((40, y), f"• Total elements: {stats['total_elements']}", fill='black', font=self.font)
        y += 25
        draw.text((40, y), f"• Text extracted: {stats.get('text_extracted', 0)}", fill='black', font=self.font)
        y += 25
        draw.text((40, y), f"• Image/table references: {stats.get('image_references', 0)}", fill='black', font=self.font)
        y += 40
        
        # Element breakdown
        draw.text((20, y), "Elements by Type:", fill='black', font=self.title_font)
        y += 35
        
        # Draw bar chart
        if stats.get('by_type'):
            max_count = max(stats['by_type'].values())
            
            for elem_type, count in sorted(stats['by_type'].items()):
                # Draw bar
                bar_length = int((count / max_count) * 400) if max_count > 0 else 0
                color = self.ELEMENT_COLORS.get(elem_type, '#95a5a6')
                
                if bar_length > 0:
                    draw.rectangle([40, y, 40 + bar_length, y + 20], fill=color)
                
                # Draw label
                draw.text((40 + bar_length + 10, y), f"{elem_type}: {count}", fill='black', font=self.font)
                y += 30
        
        img.save(output_dir / "00_pipeline_summary.png")


def create_catalog_visualization(
    catalog_dir: str | Path,
    pdf_path: str | Path,
    output_dir: Optional[str | Path] = None,
    pages: Optional[List[int]] = None,
    **kwargs
) -> Path:
    """Convenience function to create catalog visualization.
    
    Args:
        catalog_dir: Directory containing the catalog
        pdf_path: Path to original PDF
        output_dir: Output directory (defaults to catalog_dir/visualizations)
        pages: Specific pages to visualize (None = all)
        **kwargs: Additional parameters for CatalogVisualizer
        
    Returns:
        Path to visualization directory
    """
    visualizer = CatalogVisualizer(**kwargs)
    return visualizer.visualize_catalog(
        Path(catalog_dir),
        Path(pdf_path),
        Path(output_dir) if output_dir else None,
        pages
    )