# Public Interface Specification

## Overview

A public interface package that provides a clean contract between document producers (ingestion) and consumers (fact_check, agents). Uses path-based image references with on-demand loading.

## Package Structure

```
src/
├── interfaces/                    # Public contracts
│   ├── __init__.py
│   ├── document.py               # Core data models
│   ├── readers.py                # Document reader interfaces
│   └── content_types.py          # Enums and types
```

## 1. Core Data Models

### `src/interfaces/document.py`

```python
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


class Document(BaseModel):
    """A processed document with structured content."""
    # Source information
    source: str  # Original PDF path/URI
    cache_dir: Optional[str] = None  # Base directory for relative paths
    
    # Content
    blocks: List[Block]
    reading_order: List[List[str]] = Field(
        default_factory=list,
        description="List of block IDs per page in reading order"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def get_cache_path(self) -> Path:
        """Get the cache directory path."""
        if self.cache_dir:
            return Path(self.cache_dir)
        # Infer from source
        source_path = Path(self.source)
        doc_name = source_path.stem
        return source_path.parent.parent / "cache" / doc_name
    
    def save(self, path: str | Path) -> None:
        """Save document to JSON file."""
        json_str = self.model_dump_json(indent=2, exclude_none=True)
        Path(path).write_text(json_str)
    
    @classmethod
    def load(cls, path: str | Path) -> Document:
        """Load document from JSON file."""
        return cls.model_validate_json(Path(path).read_text())
```

## 2. Content Types

### `src/interfaces/content_types.py`

```python
"""Content type definitions."""

from enum import Enum


class ContentType(Enum):
    """Types of content that can be extracted."""
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    ALL = "all"


class OutputFormat(Enum):
    """Output format options for content extraction."""
    TEXT_ONLY = "text_only"                    # Pure text, no placeholders
    TEXT_WITH_PLACEHOLDERS = "placeholders"     # Text with [FIGURE 1] markers
    STRUCTURED = "structured"                   # List of content items
    VISION_READY = "vision"                     # For vision LLMs


class BlockRole(Enum):
    """Standard block roles."""
    TEXT = "Text"
    TITLE = "Title"
    LIST = "List"
    FIGURE = "Figure"
    TABLE = "Table"
```

## 3. Document Readers

### `src/interfaces/readers.py`

```python
"""Document reader interfaces and implementations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image
import base64
from io import BytesIO

from .document import Document, Block
from .content_types import ContentType, OutputFormat


class ContentItem:
    """A content item with optional image loading."""
    
    def __init__(
        self,
        block: Block,
        base_path: Path,
        page_index: int
    ):
        self.block = block
        self.base_path = base_path
        self.page_index = page_index
        self._image_cache: Optional[Image.Image] = None
    
    @property
    def type(self) -> str:
        """Get content type."""
        return self.block.role.lower()
    
    @property
    def text(self) -> Optional[str]:
        """Get text content."""
        return self.block.text
    
    @property
    def image_path(self) -> Optional[Path]:
        """Get full image path."""
        if self.block.image_path:
            return self.base_path / self.block.image_path
        return None
    
    def load_image(self) -> Optional[Image.Image]:
        """Load image from disk (cached)."""
        if not self.image_path or not self.image_path.exists():
            return None
            
        if self._image_cache is None:
            self._image_cache = Image.open(self.image_path)
        return self._image_cache
    
    def get_image_base64(self) -> Optional[str]:
        """Get image as base64 string."""
        image = self.load_image()
        if not image:
            return None
            
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = {
            "id": self.block.id,
            "type": self.type,
            "page": self.page_index,
            "bbox": self.block.bbox,
        }
        
        if self.text:
            data["text"] = self.text
        if self.block.image_path:
            data["image_path"] = str(self.block.image_path)
            
        return data


class DocumentReader(ABC):
    """Abstract base class for document readers."""
    
    @abstractmethod
    def get_content(
        self,
        content_types: List[ContentType] = None,
        output_format: OutputFormat = OutputFormat.TEXT_WITH_PLACEHOLDERS,
        page_range: Optional[Tuple[int, int]] = None
    ) -> Union[str, List[ContentItem], List[Dict[str, Any]]]:
        """Get document content with flexible options."""
        pass
    
    @abstractmethod
    def get_text_only(self) -> str:
        """Get pure text without placeholders."""
        pass
    
    @abstractmethod
    def get_vision_content(self) -> List[ContentItem]:
        """Get content items for vision processing."""
        pass


class StandardDocumentReader(DocumentReader):
    """Standard implementation of DocumentReader."""
    
    def __init__(self, document: Document, base_path: Optional[Path] = None):
        """
        Initialize reader.
        
        Args:
            document: Document to read
            base_path: Base path for images (if not provided, derived from document)
        """
        self.document = document
        
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Derive from document
            cache_path = document.get_cache_path()
            self.base_path = cache_path / "extracted"
    
    def get_content(
        self,
        content_types: List[ContentType] = None,
        output_format: OutputFormat = OutputFormat.TEXT_WITH_PLACEHOLDERS,
        page_range: Optional[Tuple[int, int]] = None
    ) -> Union[str, List[ContentItem], List[Dict[str, Any]]]:
        """Get document content with flexible options."""
        if content_types is None:
            content_types = [ContentType.ALL]
        
        # Get content items
        items = self._get_content_items(content_types, page_range)
        
        # Format output
        if output_format == OutputFormat.TEXT_ONLY:
            return self._format_text_only(items)
        elif output_format == OutputFormat.TEXT_WITH_PLACEHOLDERS:
            return self._format_with_placeholders(items)
        elif output_format == OutputFormat.STRUCTURED:
            return [item.to_dict() for item in items]
        elif output_format == OutputFormat.VISION_READY:
            return items  # Return ContentItem objects
        else:
            raise ValueError(f"Unknown output format: {output_format}")
    
    def get_text_only(self) -> str:
        """Get pure text without placeholders."""
        return self.get_content(
            content_types=[ContentType.TEXT],
            output_format=OutputFormat.TEXT_ONLY
        )
    
    def get_vision_content(self) -> List[ContentItem]:
        """Get content items for vision processing."""
        return self.get_content(
            content_types=[ContentType.ALL],
            output_format=OutputFormat.VISION_READY
        )
    
    def _get_content_items(
        self,
        content_types: List[ContentType],
        page_range: Optional[Tuple[int, int]] = None
    ) -> List[ContentItem]:
        """Get content items in reading order."""
        items = []
        
        # Determine pages to process
        if page_range:
            start_page, end_page = page_range
            pages = range(start_page, min(end_page, len(self.document.reading_order)))
        else:
            pages = range(len(self.document.reading_order))
        
        # Process each page
        for page_idx in pages:
            if page_idx >= len(self.document.reading_order):
                break
                
            block_ids = self.document.reading_order[page_idx]
            
            for block_id in block_ids:
                block = self._get_block_by_id(block_id)
                if not block:
                    continue
                
                # Filter by content type
                if not self._matches_content_type(block, content_types):
                    continue
                
                items.append(ContentItem(block, self.base_path, page_idx))
        
        return items
    
    def _get_block_by_id(self, block_id: str) -> Optional[Block]:
        """Find block by ID."""
        for block in self.document.blocks:
            if block.id == block_id:
                return block
        return None
    
    def _matches_content_type(self, block: Block, content_types: List[ContentType]) -> bool:
        """Check if block matches content type filter."""
        if ContentType.ALL in content_types:
            return True
            
        if ContentType.TEXT in content_types and block.is_text:
            return True
            
        if ContentType.FIGURE in content_types and block.role == "Figure":
            return True
            
        if ContentType.TABLE in content_types and block.role == "Table":
            return True
            
        return False
    
    def _format_text_only(self, items: List[ContentItem]) -> str:
        """Format as pure text."""
        texts = []
        
        for item in items:
            if item.text:
                texts.append(item.text)
        
        return "\n\n".join(texts)
    
    def _format_with_placeholders(self, items: List[ContentItem]) -> str:
        """Format text with figure/table placeholders."""
        texts = []
        current_page = -1
        
        for item in items:
            # Add page separator
            if item.page_index > current_page:
                if current_page >= 0:
                    texts.append(f"\n\n[Page {item.page_index + 1}]\n")
                current_page = item.page_index
            
            if item.text:
                texts.append(item.text)
            elif item.block.image_path:
                # Add placeholder
                texts.append(f"[{item.block.role.upper()} - See {item.block.image_path}]")
        
        return "\n\n".join(texts)
```

## 4. Package Initialization

### `src/interfaces/__init__.py`

```python
"""Public interfaces for document processing."""

from .document import Document, Block
from .readers import (
    DocumentReader,
    StandardDocumentReader,
    ContentItem
)
from .content_types import ContentType, OutputFormat, BlockRole

__all__ = [
    # Models
    "Document",
    "Block",
    # Readers
    "DocumentReader", 
    "StandardDocumentReader",
    "ContentItem",
    # Types
    "ContentType",
    "OutputFormat",
    "BlockRole",
]
```

## Usage Examples

### 1. Basic Text Extraction
```python
from src.interfaces import Document, StandardDocumentReader

# Load document
doc = Document.load("data/cache/FlublokPI/extracted/content.json")

# Create reader
reader = StandardDocumentReader(doc)

# Get text only
text = reader.get_text_only()

# Get text with placeholders
text_with_figs = reader.get_content()
```

### 2. Vision Agent Usage
```python
# Get content for vision LLM
items = reader.get_vision_content()

for item in items:
    if item.type == "text":
        # Add text to prompt
        messages.append({"type": "text", "text": item.text})
    elif item.type in ["figure", "table"]:
        # Load and add image
        image_base64 = item.get_image_base64()
        if image_base64:
            messages.append({
                "type": "image",
                "source": {"type": "base64", "data": image_base64}
            })
```

### 3. Structured Processing
```python
# Get structured content
content = reader.get_content(
    output_format=OutputFormat.STRUCTURED
)

# Process each item
for item in content:
    print(f"Page {item['page']}: {item['type']}")
    if 'text' in item:
        print(f"  Text: {item['text'][:50]}...")
    if 'image_path' in item:
        print(f"  Image: {item['image_path']}")
```

## Benefits

1. **Path-Based**: Efficient, no embedded images
2. **Lazy Loading**: Images loaded only when needed
3. **Flexible Output**: Multiple formats for different use cases
4. **Clean Separation**: No cross-package dependencies
5. **Type Safe**: Strong typing throughout
6. **Extensible**: Easy to add new readers or formats