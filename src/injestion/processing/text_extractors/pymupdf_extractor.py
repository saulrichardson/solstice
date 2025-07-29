"""PyMuPDF-based text extraction implementation."""

import logging
from pathlib import Path
from typing import Tuple
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO

from .base_extractor import TextExtractor, ExtractorResult
from ..text_processing_service import text_processor

logger = logging.getLogger(__name__)


class PyMuPDFExtractor(TextExtractor):
    """Text extraction using PyMuPDF library."""
    
    def extract_text_from_bbox(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        page_height: float
    ) -> ExtractorResult:
        """Extract text from PDF at specific bbox coordinates using PyMuPDF.
        
        Args:
            pdf_path: Path to PDF file
            page_num: 0-based page number
            bbox: Bounding box (x1, y1, x2, y2) in image coordinates
            page_height: Height of the page in image coordinates for conversion
            
        Returns:
            ExtractorResult containing extracted text
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Convert image coordinates to PDF coordinates
        # Image coordinates: origin at top-left, y increases downward
        # PDF coordinates: origin at bottom-left, y increases upward
        pdf_height = page.rect.height
        scale_factor = pdf_height / page_height
        
        # Convert and scale coordinates
        x1 = bbox[0] * scale_factor
        x2 = bbox[2] * scale_factor
        
        # Flip Y coordinates and scale
        y1 = pdf_height - (bbox[3] * scale_factor)  # bbox[3] is bottom in image coords
        y2 = pdf_height - (bbox[1] * scale_factor)  # bbox[1] is top in image coords
        
        # Create rect in PDF coordinate system
        rect = fitz.Rect(x1, y1, x2, y2)
        
        # Extract text from the rectangle
        text = page.get_text("text", clip=rect)
        
        doc.close()
        
        # Clean up extracted text
        text = text.strip()
        
        # Process text through the text processing service
        result = text_processor.process(text, context={
            'source': 'pymupdf',
            'pdf_path': str(pdf_path),
            'page_num': page_num,
            'bbox': bbox
        })
        
        # Build metadata
        metadata = {
            "method": "pymupdf",
            "scale_factor": scale_factor,
            "text_modified": result.was_modified,
            "processing_time": result.processing_time
        }
        
        # Add processors applied if any modifications were made
        if result.was_modified:
            metadata["processors_applied"] = result.modifications
        
        return ExtractorResult(
            text=result.text,
            confidence=1.0,  # PyMuPDF doesn't provide confidence scores
            metadata=metadata
        )
    
    def extract_figure_image(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        dpi: int = 300
    ) -> Image.Image:
        """Extract figure/table as image from PDF using PyMuPDF.
        
        Args:
            pdf_path: Path to PDF file
            page_num: 0-based page number
            bbox: Bounding box (x1, y1, x2, y2) in image coordinates
            dpi: DPI for rendering
            
        Returns:
            PIL Image of the cropped region
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # Render page at specified DPI
        mat = fitz.Matrix(dpi/72.0, dpi/72.0)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        doc.close()
        
        # Open as PIL Image and crop
        full_page = Image.open(BytesIO(img_data))
        
        # ------------------------------------------------------------------
        # The bounding box provided by upstream callers is specified in the
        # *same* coordinate space regardless of the output DPI (the tests use
        # hard-coded values for both the 300 dpi and 400 dpi calls).  When the
        # page is rendered at a higher DPI the resulting raster image is
        # proportionally larger, therefore we must **scale the bbox** so that
        # it still refers to the same physical region on the page.
        #
        # Example: a 200-pixel wide region extracted at 300 dpi should be
        # ~267 pixels wide when rendered at 400 dpi (ratio 400 / 300 = 1.333…).
        # Without this correction the cropped region would keep a constant
        # pixel size which fails the DPI-consistency tests.
        # ------------------------------------------------------------------

        # The reference DPI for the incoming bbox is 300 (historical default
        # of the detection pipeline).  Scale the coordinates to the requested
        # DPI to obtain the correct region in the rendered bitmap.
        scale = dpi / 300.0

        scaled_bbox = (
            int(bbox[0] * scale),
            int(bbox[1] * scale),
            int(bbox[2] * scale),
            int(bbox[3] * scale),
        )

        cropped = full_page.crop(scaled_bbox)
        
        return cropped
