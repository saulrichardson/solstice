"""Table Transformer (TATR) extractor using the correct PyPI package API.

This implementation follows the recommendations for using the table-transformer
PyPI package with proper weight loading and PDF word extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import pandas as pd
import fitz  # PyMuPDF
import json
import torch

logger = logging.getLogger(__name__)


class ProperTATRExtractor:
    """Extract table structure using table-transformer PyPI package."""
    
    def __init__(
        self,
        det_weights_path: Optional[Path] = None,
        str_weights_path: Optional[Path] = None,
        device: Optional[str] = None,
        use_pdf_words: bool = True
    ):
        """Initialize TATR extractor.
        
        Args:
            det_weights_path: Path to detection model weights
            str_weights_path: Path to structure recognition model weights  
            device: Device to run on ('cpu', 'cuda', 'mps')
            use_pdf_words: Use PDF word extraction instead of OCR
        """
        self.pipeline = None
        self.structure_recognizer = None
        
        # Default paths relative to project root
        base_path = Path(__file__).parent.parent.parent.parent / "assets" / "tatr"
        self.det_weights_path = det_weights_path or base_path / "pubtables1m_det_r18.pth"
        self.str_weights_path = str_weights_path or base_path / "tatr_v1.1_pub.pth"
        
        if device is None:
            if torch.cuda.is_available():
                device = 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'
        self.device = device
        self.use_pdf_words = use_pdf_words
        
    def _ensure_weights(self):
        """Ensure TATR weights are downloaded."""
        if not self.str_weights_path.exists():
            raise FileNotFoundError(
                f"Structure model weights not found at {self.str_weights_path}\n"
                "Run: make install-tatr"
            )
        if not self.det_weights_path.exists():
            logger.warning(f"Detection model weights not found at {self.det_weights_path}")
    
    def _load_pipeline(self):
        """Load full TATR pipeline for detection + structure."""
        if self.pipeline is None:
            try:
                from table_transformer import TableExtractionPipeline
                
                self._ensure_weights()
                logger.info(f"Loading TATR pipeline on {self.device}...")
                
                self.pipeline = TableExtractionPipeline(
                    det_model_path=str(self.det_weights_path),
                    str_model_path=str(self.str_weights_path),
                    det_device=self.device,
                    str_device=self.device,
                    easyocr_config={
                        'gpu': self.device != 'cpu',
                        'lang_list': ['en'],
                        'quantize': False
                    }
                )
                
            except ImportError:
                logger.error("table-transformer package not installed")
                raise
            except RuntimeError as e:
                if "Error(s) in loading state_dict" in str(e):
                    logger.error(
                        "Model loading failed due to incompatibility between HuggingFace models "
                        "and table-transformer package. The models have different architectures. "
                        "Please use Camelot or pdfplumber for table extraction instead."
                    )
                    raise RuntimeError(
                        "TATR models incompatible with table-transformer package. "
                        "Use 'camelot' or 'pdfplumber' for table extraction."
                    )
                else:
                    raise
            except Exception as e:
                logger.error(f"Failed to load TATR pipeline: {e}")
                raise
    
    def _load_structure_recognizer(self):
        """Load structure recognizer for cropped tables."""
        # TableStructureRecognizer is not available in table-transformer 1.0.6
        # Always use full pipeline
        logger.debug("Using full TableExtractionPipeline")
        self._load_pipeline()
    
    def extract_pdf_words(
        self,
        pdf_path: Path | str,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        detection_dpi: int = 200
    ) -> List[Dict[str, Any]]:
        """Extract word boxes from PDF for a specific region.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            bbox: Bounding box in detection coordinates
            detection_dpi: DPI used for detection
            
        Returns:
            List of word dictionaries with 'text' and 'box' keys
        """
        try:
            doc = fitz.open(str(pdf_path))
            page = doc[page_num - 1]  # 0-based
            
            # Convert detection bbox to PDF points
            scale = 72 / detection_dpi
            pdf_rect = fitz.Rect(
                bbox[0] * scale,
                bbox[1] * scale,
                bbox[2] * scale,
                bbox[3] * scale
            )
            
            # Get words in PDF coordinates
            words = page.get_text("words")
            word_dicts = []
            
            for w in words:
                word_rect = fitz.Rect(w[:4])
                if word_rect.intersects(pdf_rect):
                    # Keep coordinates in PDF space for now
                    word_dicts.append({
                        "text": w[4],
                        "box": list(w[:4])  # x0, y0, x1, y1 in PDF points
                    })
            
            doc.close()
            return word_dicts
            
        except Exception as e:
            logger.error(f"Failed to extract PDF words: {e}")
            return []
    
    def extract_from_pdf_bbox(
        self,
        pdf_path: Path | str,
        page_num: int,
        bbox: Tuple[float, float, float, float],
        detection_dpi: int = 200
    ) -> Dict[str, Any]:
        """Extract table structure from a PDF bounding box.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            bbox: Bounding box (x1, y1, x2, y2) in detection coordinates
            detection_dpi: DPI used for detection
            
        Returns:
            Dictionary with extraction results
        """
        try:
            # Convert PDF region to image
            from pdf2image import convert_from_path
            
            pages = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=detection_dpi
            )
            
            if not pages:
                return {"error": "Failed to render page", "method": "tatr"}
            
            page_image = pages[0]
            
            # Crop to table region
            cropped_image = page_image.crop(tuple(map(int, bbox)))
            
            # Get word boxes from PDF if enabled
            word_boxes = None
            if self.use_pdf_words:
                pdf_words = self.extract_pdf_words(pdf_path, page_num, bbox, detection_dpi)
                if pdf_words:
                    # Convert PDF coordinates to image coordinates relative to crop
                    word_boxes = []
                    scale = detection_dpi / 72
                    pdf_bbox_scaled = [c * scale for c in bbox]
                    
                    for w in pdf_words:
                        # Scale to detection DPI and make relative to crop
                        img_box = [
                            (w["box"][0] * scale) - pdf_bbox_scaled[0],
                            (w["box"][1] * scale) - pdf_bbox_scaled[1],
                            (w["box"][2] * scale) - pdf_bbox_scaled[0],
                            (w["box"][3] * scale) - pdf_bbox_scaled[1]
                        ]
                        word_boxes.append({
                            "text": w["text"],
                            "box": img_box
                        })
            
            # Load and run the pipeline
            self._load_pipeline()
            
            # Run pipeline on cropped image
            # The pipeline returns: (table_objects, table_cells_coordinates, table_cells_text)
            try:
                # Save image temporarily as the pipeline expects a path
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    cropped_image.save(tmp.name)
                    tmp_path = tmp.name
                
                table_objects, table_cells_coordinates, table_cells_text = self.pipeline(tmp_path)
                
                # Clean up temp file
                import os
                os.unlink(tmp_path)
                
            except Exception as e:
                logger.error(f"Pipeline execution failed: {e}")
                raise
            
            # Process results
            if table_objects and len(table_objects) > 0:
                # Reconstruct table from cells
                df = pd.DataFrame()
                
                if table_cells_text and len(table_cells_text) > 0:
                    # Convert cells text to DataFrame
                    try:
                        # table_cells_text is a list of lists (rows of cells)
                        df = pd.DataFrame(table_cells_text)
                    except Exception as e:
                        logger.warning(f"Failed to create DataFrame from cells: {e}")
                
                result = {
                    "objects": table_objects[0] if table_objects else [],
                    "cells": table_cells_coordinates[0] if table_cells_coordinates else [],
                    "dataframe": df,
                    "shape": df.shape if not df.empty else (0, 0),
                    "method": "tatr-pipeline",
                    "used_pdf_words": False  # Pipeline uses its own OCR
                }
                
                # Generate HTML from DataFrame
                if not df.empty:
                    result["html"] = df.to_html(index=False)
                    result["markdown"] = df.to_markdown(index=False)
                    result["json_data"] = json.loads(df.to_json(orient="split"))
                else:
                    result["html"] = ""
                    result["markdown"] = ""
                    result["json_data"] = {"columns": [], "data": []}
                
                return result
            else:
                return {
                    "error": "No table detected in region",
                    "method": "tatr"
                }
            
        except Exception as e:
            logger.error(f"TATR extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "method": "tatr",
                "html": "",
                "cells": [],
                "dataframe": pd.DataFrame()
            }