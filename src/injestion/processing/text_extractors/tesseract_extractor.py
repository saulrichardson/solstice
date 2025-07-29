"""Tesseract OCR text extractor."""

import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import subprocess
from PIL import Image
import pytesseract

from .base_extractor import TextExtractor, ExtractorResult

logger = logging.getLogger(__name__)


class TesseractExtractor:
    """Tesseract OCR text extractor with optimized settings."""
    
    def __init__(self, 
                 lang: str = 'eng',
                 config: str = '--psm 3 --oem 3',
                 **kwargs):
        """
        Initialize Tesseract extractor.
        
        Args:
            lang: Language for OCR (default: 'eng')
            config: Tesseract config string
                PSM modes:
                  3 = Fully automatic page segmentation (default)
                  6 = Uniform block of text
                  11 = Sparse text
                OEM modes:
                  3 = Default (LSTM + legacy)
        """
        super().__init__(**kwargs)
        self.lang = lang
        self.tesseract_config = config
        
        # Check if Tesseract is installed
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Using Tesseract version: {version}")
        except Exception as e:
            logger.error(f"Tesseract not found: {e}")
            raise RuntimeError("Tesseract is not installed or not in PATH")
    
    def extract_text_from_bbox(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: tuple[float, float, float, float],
        page_height: float
    ) -> ExtractorResult:
        """Extract text from PDF at specific bbox coordinates using Tesseract."""
        
        import fitz  # PyMuPDF for rendering
        
        # Open PDF
        doc = fitz.open(str(pdf_path))
        page = doc[page_num]
        
        # Use a fixed high DPI for OCR (300 is standard for good OCR)
        dpi = 300
        
        # Convert bbox to page coordinates
        x0, y0, x1, y1 = bbox
        rect = fitz.Rect(x0, y0, x1, y1)
        
        # Render the bbox area at high DPI
        mat = fitz.Matrix(dpi/72.0, dpi/72.0)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Apply preprocessing for better OCR
        img = self._preprocess_image(img)
        
        # Run Tesseract
        try:
            text = pytesseract.image_to_string(
                img, 
                lang=self.lang,
                config=self.tesseract_config
            ).strip()
            
            # Get confidence scores
            data = pytesseract.image_to_data(
                img,
                lang=self.lang,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence (excluding -1 values)
            confidences = [c for c in data['conf'] if c > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            doc.close()
            
            return ExtractorResult(
                text=text,
                confidence=avg_confidence / 100.0,  # Convert to 0-1 range
                metadata={
                    'method': 'tesseract',
                    'lang': self.lang,
                    'dpi': dpi,
                    'num_words': len([w for w in data['text'] if w.strip()])
                }
            )
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            doc.close()
            return ExtractorResult(text="", confidence=0.0)
    
    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to grayscale if not already
        if img.mode != 'L':
            img = img.convert('L')
        
        # Enhance contrast
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        
        # Apply slight sharpening
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.2)
        
        return img
    
    def extract_from_image(self, image_path: str) -> str:
        """Extract text directly from an image file."""
        try:
            img = Image.open(image_path)
            img = self._preprocess_image(img)
            
            text = pytesseract.image_to_string(
                img,
                lang=self.lang,
                config=self.tesseract_config
            ).strip()
            
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from {image_path}: {e}")
            return ""


# Import io for BytesIO
import io