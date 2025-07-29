"""Abstract base class for text extraction from PDF documents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image


def calculate_dpi_from_page_height(page_height: float, standard_height: float = 792.0) -> int:
    """Calculate DPI from page height in pixels.
    
    Args:
        page_height: Height of the page in pixels (e.g., 4400 for 400 DPI)
        standard_height: Standard page height in points (default: 792 for US Letter)
        
    Returns:
        DPI value
        
    Example:
        >>> calculate_dpi_from_page_height(4400)  # Returns 400
        >>> calculate_dpi_from_page_height(3300)  # Returns 300
    """
    return int(page_height / standard_height * 72)


@dataclass
class ExtractorResult:
    """Result from text extraction operation."""
    text: str
    confidence: Optional[float] = None
    metadata: Optional[dict] = None


class TextExtractor(ABC):
    """Abstract base class for text extraction implementations."""
    
    def __init__(self, **kwargs):
        """Initialize the extractor with optional configuration."""
        self.config = kwargs
    
    @abstractmethod
    def extract_text_from_bbox(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        page_height: float
    ) -> ExtractorResult:
        """Extract text from PDF at specific bbox coordinates.
        
        Args:
            pdf_path: Path to PDF file
            page_num: 0-based page number
            bbox: Bounding box (x1, y1, x2, y2) in image coordinates
            page_height: Height of the page in image coordinates for conversion
            
        Returns:
            ExtractorResult containing extracted text and metadata
            
        Important:
            The bbox coordinates MUST match the DPI implied by page_height.
            For US Letter (792 points):
            - page_height = 3300 → 300 DPI (3300/792*72 = 300)
            - page_height = 4400 → 400 DPI (4400/792*72 = 400)
            
            Implementations should calculate DPI as:
            dpi = int(page_height / standard_height * 72)
            where standard_height = 792 for US Letter
        """
        pass
    
    @abstractmethod
    def extract_figure_image(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        dpi: int = 300
    ) -> Image.Image:
        """Extract figure/table as image from PDF.
        
        Args:
            pdf_path: Path to PDF file
            page_num: 0-based page number
            bbox: Bounding box (x1, y1, x2, y2) in image coordinates
            dpi: DPI for rendering
            
        Returns:
            PIL Image of the cropped region
        """
        pass
    
    def batch_extract(
        self,
        pdf_path: Path,
        extractions: List[Tuple[int, Tuple[float, float, float, float]]],
        page_heights: List[float]
    ) -> List[ExtractorResult]:
        """Batch extract text from multiple bounding boxes.
        
        Default implementation calls extract_text_from_bbox for each bbox.
        Subclasses can override for more efficient batch processing.
        
        Args:
            pdf_path: Path to PDF file
            extractions: List of (page_num, bbox) tuples
            page_heights: List of page heights for coordinate conversion
            
        Returns:
            List of ExtractorResult objects
        """
        results = []
        for page_num, bbox in extractions:
            result = self.extract_text_from_bbox(
                pdf_path, page_num, bbox, page_heights[page_num]
            )
            results.append(result)
        return results
    
    def cleanup(self):
        """Clean up any resources held by the extractor."""
        pass