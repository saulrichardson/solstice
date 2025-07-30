"""Core document data models."""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field


class Block(BaseModel):
    """A content block in the document."""
    id: str
    page_index: int
    role: str  # 'Text', 'Title', 'Figure', 'Table', 'List'
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    
    # Content (one of these will be populated)
    text: Optional[str] = None
    html: Optional[str] = None  # For tables (keeping for compatibility)
    image_path: Optional[str] = None  # Relative path to image file
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def is_text(self) -> bool:
        """Check if this is a text block."""
        return self.role in ['Text', 'Title', 'List'] and self.text is not None
    
    @property
    def is_visual(self) -> bool:
        """Check if this is a visual block (figure/table)."""
        return self.role in ['Figure', 'Table'] and self.image_path is not None
    
    def get_detection_dpi(self) -> Optional[int]:
        """Get the DPI at which this block was detected."""
        return self.metadata.get('detection_dpi')


class Document(BaseModel):
    """A processed document with structured content."""
    source_pdf: str = Field(..., description="Original PDF path or URI")
    cache_dir: Optional[str] = None  # Base directory for relative paths
    
    # Content
    blocks: List[Block]
    reading_order: List[List[str]] = Field(
        default_factory=list,
        description="List of block IDs per page in reading order"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Pipeline tracking metadata
    pipeline_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tracking information about pipeline transformations"
    )
    
    @property
    def source(self) -> str:
        """Alias for source_pdf for cleaner API."""
        return self.source_pdf
    
    def get_cache_path(self) -> Path:
        """Get the cache directory path."""
        if self.cache_dir:
            return Path(self.cache_dir)
        # Infer from source using settings
        from src.core.config import settings
        source_path = Path(self.source_pdf)
        doc_name = source_path.stem
        # Use configured cache directory
        return Path(settings.filesystem_cache_dir) / doc_name
    
    def save(self, path: str | Path) -> None:
        """Save document to JSON file."""
        json_str = self.model_dump_json(indent=2, exclude_none=True)
        Path(path).write_text(json_str)
    
    @classmethod
    def load(cls, path: str | Path) -> Document:
        """Load document from JSON file."""
        return cls.model_validate_json(Path(path).read_text())