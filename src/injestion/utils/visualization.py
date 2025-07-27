"""
Utilities for DPI-aware visualization of layout detection results.

This module ensures consistent coordinate handling across different DPI settings
to prevent misalignment between detected bounding boxes and visualizations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pdf2image import convert_from_path
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Default DPI used by pdf2image and layout detection models
DEFAULT_DETECTION_DPI = 200


@dataclass
class BoundingBox:
    """DPI-aware bounding box representation"""
    x1: float
    y1: float
    x2: float
    y2: float
    dpi: int = DEFAULT_DETECTION_DPI
    
    def scale_to_dpi(self, target_dpi: int) -> 'BoundingBox':
        """Scale coordinates to match a different DPI"""
        if target_dpi == self.dpi:
            return self
        
        scale = target_dpi / self.dpi
        return BoundingBox(
            x1=self.x1 * scale,
            y1=self.y1 * scale,
            x2=self.x2 * scale,
            y2=self.y2 * scale,
            dpi=target_dpi
        )
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1


class LayoutVisualizer:
    """DPI-aware layout visualization handler"""
    
    # Standard color schemes
    DEFAULT_COLORS = {
        "Text": "#3498db",
        "Title": "#e74c3c", 
        "List": "#2ecc71",
        "ListItem": "#27ae60",
        "Table": "#f39c12",
        "Figure": "#9b59b6",
    }
    
    def __init__(self, detection_dpi: int = DEFAULT_DETECTION_DPI):
        """
        Initialize visualizer with detection DPI.
        
        Args:
            detection_dpi: DPI at which layout detection was performed
        """
        self.detection_dpi = detection_dpi
        logger.info(f"Initialized LayoutVisualizer with detection DPI: {detection_dpi}")
    
    def load_and_scale_pdf_page(
        self, 
        pdf_path: Union[str, Path], 
        page_num: int = 1,
        visualization_dpi: int = 150
    ) -> Tuple[np.ndarray, float]:
        """
        Load PDF page and calculate scaling factor.
        
        Returns:
            Tuple of (page_image, scale_factor)
        """
        pdf_path = Path(pdf_path)
        
        # Convert at visualization DPI
        images = convert_from_path(
            pdf_path, 
            first_page=page_num, 
            last_page=page_num,
            dpi=visualization_dpi
        )
        page_image = np.array(images[0])
        
        # Calculate scale factor
        scale_factor = visualization_dpi / self.detection_dpi
        
        logger.debug(
            f"Loaded page {page_num} at {visualization_dpi} DPI. "
            f"Scale factor: {scale_factor:.3f}"
        )
        
        return page_image, scale_factor
    
    def visualize_layout(
        self,
        pdf_path: Union[str, Path],
        layout_data: Union[str, Path, Dict, List],
        page_num: int = 1,
        visualization_dpi: int = 150,
        output_path: Optional[Union[str, Path]] = None,
        show_labels: bool = True,
        show_confidence: bool = True,
        colors: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Create DPI-aware visualization of layout detection results.
        
        Args:
            pdf_path: Path to PDF file
            layout_data: Layout detection results (JSON file path or data)
            page_num: Page number to visualize (1-indexed)
            visualization_dpi: DPI for output visualization
            output_path: Where to save visualization (if None, displays)
            show_labels: Whether to show element type labels
            show_confidence: Whether to show confidence scores
            colors: Custom color mapping (uses defaults if None)
        """
        # Load layout data
        if isinstance(layout_data, (str, Path)):
            with open(layout_data, 'r') as f:
                data = json.load(f)
        else:
            data = layout_data
        
        # Handle different data formats
        if isinstance(data, list) and len(data) >= page_num:
            # List of pages
            page_data = data[page_num - 1]
            elements = page_data.get('elements', page_data)
        elif isinstance(data, dict):
            elements = data.get('elements', [])
        else:
            elements = data
        
        # Load page image and get scale factor
        page_image, scale_factor = self.load_and_scale_pdf_page(
            pdf_path, page_num, visualization_dpi
        )
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 16))
        ax.imshow(page_image)
        
        # Use custom colors or defaults
        element_colors = colors or self.DEFAULT_COLORS
        
        # Draw each element with scaled coordinates
        for i, elem in enumerate(elements):
            # Extract bbox based on format
            if 'bbox' in elem:
                bbox_data = elem['bbox']
                if isinstance(bbox_data, dict):
                    bbox = BoundingBox(
                        x1=bbox_data['x1'],
                        y1=bbox_data['y1'],
                        x2=bbox_data['x2'],
                        y2=bbox_data['y2'],
                        dpi=self.detection_dpi
                    )
                else:
                    bbox = BoundingBox(*bbox_data, dpi=self.detection_dpi)
            else:
                # Handle other formats
                continue
            
            # Scale bbox to visualization DPI
            scaled_bbox = bbox.scale_to_dpi(visualization_dpi)
            
            # Get element properties
            elem_type = elem.get('type', elem.get('label', 'Unknown'))
            confidence = elem.get('score', elem.get('confidence', 1.0))
            color = element_colors.get(elem_type, '#888888')
            
            # Draw rectangle
            rect = patches.Rectangle(
                (scaled_bbox.x1, scaled_bbox.y1),
                scaled_bbox.width,
                scaled_bbox.height,
                linewidth=2,
                edgecolor=color,
                facecolor='none',
                alpha=0.8
            )
            ax.add_patch(rect)
            
            # Add labels
            if show_labels or show_confidence:
                label_parts = []
                if show_labels:
                    label_parts.append(elem_type)
                if show_confidence:
                    label_parts.append(f"{confidence:.2f}")
                
                label = " ".join(label_parts)
                ax.text(
                    scaled_bbox.x1,
                    scaled_bbox.y1 - 5,
                    label,
                    color=color,
                    fontsize=10,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8)
                )
        
        # Configure plot
        ax.set_title(
            f"Layout Detection - Page {page_num} "
            f"(Visualization: {visualization_dpi} DPI, Detection: {self.detection_dpi} DPI)",
            fontsize=14,
            pad=20
        )
        ax.set_xticks([])
        ax.set_yticks([])
        
        # Add scale factor info if different from 1.0
        if abs(scale_factor - 1.0) > 0.01:
            ax.text(
                0.02, 0.98, f"Coordinate scaling: {scale_factor:.2f}x",
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7)
            )
        
        plt.tight_layout()
        
        # Save or show
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved visualization to {output_path}")
        else:
            plt.show()
        
        plt.close()


def add_dpi_metadata_to_results(
    results: Union[Dict, List],
    dpi: int = DEFAULT_DETECTION_DPI
) -> Union[Dict, List]:
    """
    Add DPI metadata to detection results for future reference.
    
    Args:
        results: Detection results
        dpi: DPI at which detection was performed
        
    Returns:
        Results with added DPI metadata
    """
    if isinstance(results, list):
        # List of pages
        for page in results:
            if isinstance(page, dict):
                page['detection_dpi'] = dpi
    elif isinstance(results, dict):
        results['detection_dpi'] = dpi
    
    return results


def validate_dpi_consistency(
    pdf_path: Union[str, Path],
    results: Union[Dict, List],
    expected_dpi: int = DEFAULT_DETECTION_DPI
) -> bool:
    """
    Validate that detection results match expected DPI.
    
    Args:
        pdf_path: Path to PDF file
        results: Detection results
        expected_dpi: Expected detection DPI
        
    Returns:
        True if coordinates appear consistent with DPI
    """
    # Get page dimensions at expected DPI
    images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=expected_dpi)
    expected_width, expected_height = images[0].size
    
    # Check if any coordinates exceed expected dimensions
    max_x = 0
    max_y = 0
    
    if isinstance(results, list):
        elements = results[0].get('elements', []) if results else []
    else:
        elements = results.get('elements', [])
    
    for elem in elements:
        bbox = elem.get('bbox', {})
        if isinstance(bbox, dict):
            max_x = max(max_x, bbox.get('x2', 0))
            max_y = max(max_y, bbox.get('y2', 0))
        elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])
    
    # Allow 5% margin for rounding errors
    margin = 0.05
    width_ok = max_x <= expected_width * (1 + margin)
    height_ok = max_y <= expected_height * (1 + margin)
    
    if not (width_ok and height_ok):
        logger.warning(
            f"DPI mismatch detected! Max coordinates ({max_x}, {max_y}) "
            f"exceed expected dimensions ({expected_width}, {expected_height}) at {expected_dpi} DPI"
        )
        return False
    
    return True


# Convenience function for quick visualization
def visualize_with_auto_dpi(
    pdf_path: Union[str, Path],
    results_path: Union[str, Path],
    page_num: int = 1,
    output_path: Optional[Union[str, Path]] = None
) -> None:
    """
    Automatically handle DPI scaling for visualization.
    
    This function attempts to detect the DPI from the results
    or uses the default detection DPI.
    """
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    # Try to get DPI from results metadata
    if isinstance(results, list) and results:
        detection_dpi = results[0].get('detection_dpi', DEFAULT_DETECTION_DPI)
    elif isinstance(results, dict):
        detection_dpi = results.get('detection_dpi', DEFAULT_DETECTION_DPI)
    else:
        detection_dpi = DEFAULT_DETECTION_DPI
    
    # Create visualizer and render
    visualizer = LayoutVisualizer(detection_dpi=detection_dpi)
    visualizer.visualize_layout(
        pdf_path=pdf_path,
        layout_data=results,
        page_num=page_num,
        output_path=output_path
    )


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python visualization.py <pdf_path> <results_json>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    results_file = sys.argv[2]
    
    visualize_with_auto_dpi(pdf_file, results_file)