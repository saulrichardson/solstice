"""Component-specific extractors for different document elements.

This module provides specialized extractors for text, tables, and figures,
routing each component type to the most appropriate extraction method.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import numpy as np
import pdfplumber
import pandas as pd
import camelot
from io import BytesIO

logger = logging.getLogger(__name__)


class TextExtractor:
    """Extract text content from PDF regions."""
    
    def __init__(self):
        self.pdf = None
        self.current_page = None
    
    def extract_from_bbox(
        self, 
        pdf_path: Path | str,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        detection_dpi: int = 200
    ) -> Dict[str, Any]:
        """Extract text from a specific bounding box.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            bbox: Bounding box (x1, y1, x2, y2) in detection coordinates
            detection_dpi: DPI used for detection (for coordinate conversion)
            
        Returns:
            Dictionary with extracted text and metadata
        """
        pdf_path = Path(pdf_path)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num > len(pdf.pages):
                    logger.error(f"Page {page_num} not found in PDF")
                    return {"text": "", "error": "Page not found"}
                
                page = pdf.pages[page_num - 1]
                
                # Convert detection coordinates to PDF coordinates
                # pdfplumber uses 72 DPI by default
                scale = 72 / detection_dpi
                pdf_bbox = (
                    bbox[0] * scale,
                    bbox[1] * scale,
                    bbox[2] * scale,
                    bbox[3] * scale
                )
                
                # Crop to the bounding box
                cropped = page.crop(pdf_bbox)
                
                # Extract text
                text = cropped.extract_text() or ""
                
                # Also extract words with positions for potential future use
                words = cropped.extract_words()
                
                return {
                    "text": text.strip(),
                    "word_count": len(text.split()),
                    "char_count": len(text),
                    "words_with_positions": words,
                    "bbox": bbox,
                    "pdf_bbox": pdf_bbox
                }
                
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return {
                "text": "",
                "error": str(e)
            }


class TableExtractor:
    """Extract table data from PDF regions."""
    
    def __init__(self):
        self.tatr_extractor = None
    
    def extract_from_bbox(
        self,
        pdf_path: Path | str,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        detection_dpi: int = 200,
        method: str = "camelot",
        page_image: Optional[Image.Image] = None
    ) -> Dict[str, Any]:
        """Extract table from a specific bounding box.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed) 
            bbox: Bounding box (x1, y1, x2, y2) in detection coordinates
            detection_dpi: DPI used for detection
            method: Extraction method ("camelot", "pdfplumber", or "tatr")
            page_image: Pre-rendered page image (for TATR method)
            
        Returns:
            Dictionary with extracted table data
        """
        pdf_path = Path(pdf_path)
        
        # Convert detection coordinates to PDF coordinates
        scale = 72 / detection_dpi
        pdf_bbox = (
            bbox[0] * scale,
            bbox[1] * scale,
            bbox[2] * scale,
            bbox[3] * scale
        )
        
        if method == "tatr":
            return self._extract_with_tatr(pdf_path, page_num, bbox, detection_dpi, page_image)
        elif method == "camelot":
            return self._extract_with_camelot(pdf_path, page_num, pdf_bbox)
        else:
            return self._extract_with_pdfplumber(pdf_path, page_num, pdf_bbox)
    
    def _extract_with_camelot(
        self,
        pdf_path: Path,
        page_num: int,
        pdf_bbox: Tuple[float, float, float, float]
    ) -> Dict[str, Any]:
        """Extract table using Camelot library."""
        try:
            # Camelot uses string format for table areas: "x1,y1,x2,y2"
            # Note: Camelot uses bottom-left origin, may need coordinate conversion
            table_area = f"{pdf_bbox[0]},{pdf_bbox[1]},{pdf_bbox[2]},{pdf_bbox[3]}"
            
            # Try lattice method first (for tables with visible borders)
            tables = camelot.read_pdf(
                str(pdf_path),
                pages=str(page_num),
                flavor='lattice',
                table_areas=[table_area]
            )
            
            if not tables or len(tables) == 0:
                # Fallback to stream method (for borderless tables)
                tables = camelot.read_pdf(
                    str(pdf_path),
                    pages=str(page_num),
                    flavor='stream',
                    table_areas=[table_area]
                )
            
            if tables and len(tables) > 0:
                table = tables[0]
                
                return {
                    "data": table.df.to_dict('records'),
                    "dataframe": table.df,
                    "shape": table.df.shape,
                    "parsing_report": table.parsing_report,
                    "accuracy": table.accuracy,
                    "method": "camelot"
                }
            else:
                return {
                    "data": [],
                    "error": "No table found in region",
                    "method": "camelot"
                }
                
        except Exception as e:
            logger.error(f"Camelot extraction failed: {e}")
            # Fallback to pdfplumber
            return self._extract_with_pdfplumber(pdf_path, page_num, pdf_bbox)
    
    def _extract_with_pdfplumber(
        self,
        pdf_path: Path,
        page_num: int,
        pdf_bbox: Tuple[float, float, float, float]
    ) -> Dict[str, Any]:
        """Extract table using pdfplumber as fallback."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num - 1]
                
                # Crop to the bounding box
                cropped = page.crop(pdf_bbox)
                
                # Extract tables
                tables = cropped.extract_tables()
                
                if tables and len(tables) > 0:
                    # Convert to DataFrame for consistency
                    df = pd.DataFrame(tables[0])
                    
                    # Clean up the DataFrame
                    # First row might be headers
                    if len(df) > 1:
                        df.columns = df.iloc[0]
                        df = df.iloc[1:].reset_index(drop=True)
                    
                    return {
                        "data": df.to_dict('records'),
                        "dataframe": df,
                        "shape": df.shape,
                        "method": "pdfplumber"
                    }
                else:
                    # Try to extract as structured text
                    text = cropped.extract_text()
                    
                    return {
                        "data": [],
                        "raw_text": text,
                        "error": "No structured table found, extracted as text",
                        "method": "pdfplumber"
                    }
                    
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return {
                "data": [],
                "error": str(e),
                "method": "pdfplumber"
            }
    
    def _extract_with_tatr(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        detection_dpi: int,
        page_image: Optional[Image.Image] = None
    ) -> Dict[str, Any]:
        """Extract table using Table Transformer (TATR) with official package."""
        try:
            # Lazy import and initialization
            if self.tatr_extractor is None:
                from .tatr_extractor import TATRStructureExtractor
                self.tatr_extractor = TATRStructureExtractor()
            
            # Use the new TATR extractor
            result = self.tatr_extractor.extract_from_pdf_bbox(
                pdf_path,
                page_num,
                bbox,
                detection_dpi,
                extraction_dpi=300  # Recommended for TATR
            )
            
            # Convert to expected format
            if "error" not in result:
                return {
                    "data": result.get("json_data", {}).get("data", []),
                    "dataframe": result.get("dataframe"),
                    "shape": result.get("shape"),
                    "method": "tatr",
                    "html": result.get("html"),
                    "markdown": result.get("markdown"),
                    "cells": result.get("cells", [])
                }
            else:
                # Fallback to camelot on error
                logger.warning(f"TATR failed: {result['error']}, falling back to camelot")
                return self._extract_with_camelot(pdf_path, page_num, bbox)
                
        except Exception as e:
            logger.error(f"TATR extraction failed: {e}")
            # Fallback to camelot
            return self._extract_with_camelot(pdf_path, page_num, bbox)


class FigureExtractor:
    """Extract figure/image data from PDF regions."""
    
    def extract_from_bbox(
        self,
        pdf_path: Path | str,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        page_image: Optional[Image.Image] = None,
        detection_dpi: int = 200,
        extract_dpi: int = 300
    ) -> Dict[str, Any]:
        """Extract figure from a specific bounding box.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            bbox: Bounding box (x1, y1, x2, y2) in detection coordinates
            page_image: Pre-rendered page image (optional)
            detection_dpi: DPI used for detection
            extract_dpi: DPI for figure extraction
            
        Returns:
            Dictionary with extracted figure data
        """
        pdf_path = Path(pdf_path)
        
        try:
            # If page image not provided, render it
            if page_image is None:
                from pdf2image import convert_from_path
                pages = convert_from_path(
                    pdf_path, 
                    first_page=page_num,
                    last_page=page_num,
                    dpi=extract_dpi
                )
                if not pages:
                    return {"error": "Failed to render page"}
                page_image = pages[0]
            
            # Scale bbox coordinates to extraction DPI
            if detection_dpi != extract_dpi:
                scale = extract_dpi / detection_dpi
                scaled_bbox = (
                    int(bbox[0] * scale),
                    int(bbox[1] * scale),
                    int(bbox[2] * scale),
                    int(bbox[3] * scale)
                )
            else:
                scaled_bbox = tuple(map(int, bbox))
            
            # Crop the image
            cropped_image = page_image.crop(scaled_bbox)
            
            # Convert to numpy array for analysis
            img_array = np.array(cropped_image)
            
            # Basic image analysis
            is_color = len(img_array.shape) == 3 and img_array.shape[2] > 1
            has_content = img_array.std() > 10  # Not just white space
            
            # Save to bytes buffer
            buffer = BytesIO()
            cropped_image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()
            
            return {
                "image": cropped_image,
                "image_bytes": image_bytes,
                "size": cropped_image.size,
                "mode": cropped_image.mode,
                "is_color": is_color,
                "has_content": has_content,
                "bbox": bbox,
                "scaled_bbox": scaled_bbox
            }
            
        except Exception as e:
            logger.error(f"Error extracting figure: {e}")
            return {
                "error": str(e),
                "bbox": bbox
            }


class ComponentRouter:
    """Routes components to appropriate extractors."""
    
    def __init__(self):
        self.text_extractor = TextExtractor()
        self.table_extractor = TableExtractor()
        self.figure_extractor = FigureExtractor()
    
    def extract_component(
        self,
        component_type: str,
        pdf_path: Path | str,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        detection_dpi: int = 200,
        page_image: Optional[Image.Image] = None,
        table_method: str = "camelot"
    ) -> Dict[str, Any]:
        """Route component to appropriate extractor.
        
        Args:
            component_type: Type of component ("text", "table", "figure")
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            bbox: Bounding box coordinates
            detection_dpi: DPI used for detection
            page_image: Pre-rendered page image (for figures and TATR)
            table_method: Method for table extraction ("camelot", "pdfplumber", "tatr")
            
        Returns:
            Extracted content based on component type
        """
        if component_type.lower() in ["text", "title", "list"]:
            return self.text_extractor.extract_from_bbox(
                pdf_path, page_num, bbox, detection_dpi
            )
        elif component_type.lower() == "table":
            return self.table_extractor.extract_from_bbox(
                pdf_path, page_num, bbox, detection_dpi, 
                method=table_method, page_image=page_image
            )
        elif component_type.lower() == "figure":
            return self.figure_extractor.extract_from_bbox(
                pdf_path, page_num, bbox, page_image, detection_dpi
            )
        else:
            logger.warning(f"Unknown component type: {component_type}")
            return {"error": f"Unknown component type: {component_type}"}