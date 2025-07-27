"""Table Transformer (TATR) extractor using the official table-transformer package.

This module implements the recommended approach for table structure recognition
using TATR v1.1 with PubTables-1M weights.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import numpy as np
import pandas as pd
import fitz  # PyMuPDF
import json
from io import StringIO
import os

logger = logging.getLogger(__name__)


class TATRStructureExtractor:
    """Extract table structure using Table Transformer v1.1."""
    
    def __init__(self, weights_path: Optional[str] = None):
        """Initialize TATR extractor.
        
        Args:
            weights_path: Path to TATR weights. If None, uses default cache location.
        """
        self.extractor = None
        self.weights_path = weights_path or os.path.expanduser("~/.cache/tatr/tatr_v1.1_pub.pth")
        
    def _ensure_weights(self):
        """Ensure TATR weights are downloaded."""
        if not os.path.exists(self.weights_path):
            logger.info(f"TATR weights not found at {self.weights_path}")
            logger.info("Please download from: https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub/resolve/main/pytorch_model.bin")
            raise FileNotFoundError(f"TATR weights not found at {self.weights_path}")
    
    def _load_model(self):
        """Load TATR model on demand."""
        if self.extractor is None:
            try:
                from tatr.inference import TableExtractor
                self._ensure_weights()
                logger.info("Loading TATR model...")
                self.extractor = TableExtractor(weights=self.weights_path)
            except ImportError:
                logger.error("table-transformer package not installed. Run: pip install table-transformer[pytesseract]")
                raise
    
    def extract_from_pdf_bbox(
        self,
        pdf_path: Path | str,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        detection_dpi: int = 200,
        extraction_dpi: int = 300
    ) -> Dict[str, Any]:
        """Extract table structure from a PDF bounding box.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            bbox: Bounding box (x1, y1, x2, y2) in detection coordinates
            detection_dpi: DPI used for detection
            extraction_dpi: DPI for extraction (300 recommended for TATR)
            
        Returns:
            Dictionary with:
            - html: Full HTML table with structure
            - cells: List of cell dictionaries
            - dataframe: Pandas DataFrame
            - markdown: Markdown representation
            - json_data: JSON representation
        """
        self._load_model()
        
        try:
            # Open PDF
            doc = fitz.open(str(pdf_path))
            page = doc[page_num - 1]  # 0-based
            
            # Convert detection bbox to PDF points
            detection_to_pdf_scale = 72 / detection_dpi
            pdf_rect = fitz.Rect(
                bbox[0] * detection_to_pdf_scale,
                bbox[1] * detection_to_pdf_scale,
                bbox[2] * detection_to_pdf_scale,
                bbox[3] * detection_to_pdf_scale
            )
            
            # Get word boxes from PDF (best quality)
            words = page.get_text("words")
            word_dicts = []
            
            for w in words:
                word_rect = fitz.Rect(w[:4])
                if word_rect.intersects(pdf_rect):
                    # Convert word coordinates relative to table crop
                    word_dicts.append({
                        "text": w[4],
                        "box": [
                            (w[0] - pdf_rect.x0) * extraction_dpi / 72,
                            (w[1] - pdf_rect.y0) * extraction_dpi / 72,
                            (w[2] - pdf_rect.x0) * extraction_dpi / 72,
                            (w[3] - pdf_rect.y0) * extraction_dpi / 72
                        ]
                    })
            
            # Extract table crop at high DPI
            mat = fitz.Matrix(extraction_dpi / 72)
            pix = page.get_pixmap(matrix=mat, clip=pdf_rect)
            
            # Convert to PIL Image
            img_data = pix.tobytes()
            img = Image.open(StringIO(img_data))
            
            # Run TATR
            html, cells = self.extractor.extract(img, word_dicts)
            
            # Convert to DataFrame
            df = pd.read_html(html)[0] if html else pd.DataFrame()
            
            # Convert to various formats
            result = {
                "html": html,
                "cells": cells,
                "dataframe": df,
                "shape": df.shape,
                "method": "tatr"
            }
            
            # Add markdown representation
            if not df.empty:
                result["markdown"] = df.to_markdown(index=False)
                result["json_data"] = json.loads(df.to_json(orient="split"))
            else:
                result["markdown"] = ""
                result["json_data"] = {"columns": [], "data": []}
            
            doc.close()
            return result
            
        except Exception as e:
            logger.error(f"TATR extraction failed: {e}")
            return {
                "error": str(e),
                "method": "tatr",
                "html": "",
                "cells": [],
                "dataframe": pd.DataFrame()
            }
    
    def extract_from_image(
        self,
        image: Image.Image,
        word_boxes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Extract table structure from an image.
        
        Args:
            image: PIL Image of the table
            word_boxes: Optional list of word dictionaries with 'text' and 'box' keys
            
        Returns:
            Dictionary with extraction results
        """
        self._load_model()
        
        try:
            # If no word boxes provided, use OCR
            if word_boxes is None:
                try:
                    import pytesseract
                    # Get word-level data from Tesseract
                    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    word_boxes = []
                    
                    for i in range(len(data['text'])):
                        if data['text'][i].strip():
                            word_boxes.append({
                                "text": data['text'][i],
                                "box": [
                                    data['left'][i],
                                    data['top'][i],
                                    data['left'][i] + data['width'][i],
                                    data['top'][i] + data['height'][i]
                                ]
                            })
                except ImportError:
                    logger.warning("pytesseract not available, TATR will use internal OCR")
                    word_boxes = []
            
            # Run TATR
            html, cells = self.extractor.extract(image, word_boxes)
            
            # Convert to DataFrame
            df = pd.read_html(html)[0] if html else pd.DataFrame()
            
            result = {
                "html": html,
                "cells": cells,
                "dataframe": df,
                "shape": df.shape,
                "method": "tatr"
            }
            
            # Add markdown representation
            if not df.empty:
                result["markdown"] = df.to_markdown(index=False)
                result["json_data"] = json.loads(df.to_json(orient="split"))
            else:
                result["markdown"] = ""
                result["json_data"] = {"columns": [], "data": []}
            
            return result
            
        except Exception as e:
            logger.error(f"TATR image extraction failed: {e}")
            return {
                "error": str(e),
                "method": "tatr",
                "html": "",
                "cells": [],
                "dataframe": pd.DataFrame()
            }


def download_tatr_weights(force: bool = False):
    """Download TATR weights if not present.
    
    Args:
        force: Force re-download even if weights exist
    """
    weights_path = os.path.expanduser("~/.cache/tatr/tatr_v1.1_pub.pth")
    weights_dir = os.path.dirname(weights_path)
    
    if os.path.exists(weights_path) and not force:
        logger.info(f"TATR weights already exist at {weights_path}")
        return weights_path
    
    # Create directory
    os.makedirs(weights_dir, exist_ok=True)
    
    # Download weights
    import urllib.request
    url = "https://huggingface.co/microsoft/table-transformer-structure-recognition-v1.1-pub/resolve/main/pytorch_model.bin"
    
    logger.info(f"Downloading TATR weights from {url}")
    logger.info(f"This may take a while (file is ~400MB)...")
    
    try:
        urllib.request.urlretrieve(url, weights_path)
        logger.info(f"Downloaded TATR weights to {weights_path}")
        return weights_path
    except Exception as e:
        logger.error(f"Failed to download TATR weights: {e}")
        raise