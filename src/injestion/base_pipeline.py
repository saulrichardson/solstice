"""Base pipeline class for consistent PDF processing architecture."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Type
from abc import ABC, abstractmethod

from pdf2image import convert_from_path
from src.interfaces import Document
from .storage.paths import pages_dir, stage_dir
from .config import IngestionConfig, DEFAULT_CONFIG


class BasePDFPipeline(ABC):
    """Abstract base class for PDF processing pipelines.
    
    Provides common structure for all document processing pipelines while
    allowing specialization of detection and consolidation strategies.
    """
    
    def __init__(self, config: Optional[IngestionConfig] = None):
        """Initialize pipeline with configuration.
        
        Parameters
        ----------
        config : IngestionConfig, optional
            Pipeline configuration. Uses DEFAULT_CONFIG if not provided.
        """
        self.config = config or DEFAULT_CONFIG
        self.detector = self._create_detector()
        self.consolidator = self._create_consolidator()
    
    @abstractmethod
    def _create_detector(self):
        """Create the layout detector for this pipeline."""
        pass
    
    @abstractmethod
    def _create_consolidator(self):
        """Create the box consolidator for this pipeline."""
        pass
    
    def process_pdf(self, pdf_path: str | os.PathLike[str]) -> Document:
        """Process a PDF file through the pipeline.
        
        Parameters
        ----------
        pdf_path : str or Path
            Path to the PDF file to process
            
        Returns
        -------
        Document
            Processed document with layout, text, and metadata
        """
        pdf_path = Path(pdf_path)
        
        # Common step 1: Convert PDF to images
        print(f"Converting {pdf_path.name} to images...")
        images = self._convert_to_images(pdf_path)
        
        # Common step 2: Run layout detection
        print("Running layout detection...")
        layouts = self.detector.detect_images(images)
        
        # Common step 3: Apply consolidation
        print("Applying box consolidation...")
        consolidated_layouts = self._apply_consolidation(layouts, images)
        
        # Common step 4: Create document and extract content
        print("Creating document structure...")
        document = self._create_document(consolidated_layouts, pdf_path, images)
        
        # Common step 5: Save outputs and visualize
        self._save_outputs(document, pdf_path)
        
        return document
    
    def _convert_to_images(self, pdf_path: Path) -> List:
        """Convert PDF to images and save them."""
        page_dir = pages_dir(pdf_path)
        page_dir.mkdir(parents=True, exist_ok=True)
        
        images = convert_from_path(str(pdf_path), dpi=self.config.detection_dpi)
        for idx, img in enumerate(images):
            img.save(page_dir / f"page-{idx:03}.png")
        
        return images
    
    @abstractmethod
    def _apply_consolidation(self, layouts: List, images: List) -> List:
        """Apply box consolidation strategy."""
        pass
    
    @abstractmethod
    def _create_document(self, layouts: List, pdf_path: Path, images: List) -> Document:
        """Convert layouts to Document format."""
        pass
    
    @abstractmethod
    def _save_outputs(self, document: Document, pdf_path: Path):
        """Save processing outputs."""
        pass