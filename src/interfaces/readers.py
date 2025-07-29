"""Document reader interfaces and implementations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from PIL import Image
import base64
from io import BytesIO
import logging

from .document import Document, Block
from .content_types import ContentType, OutputFormat

logger = logging.getLogger(__name__)


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
        if not self.image_path:
            return None
            
        if not self.image_path.exists():
            logger.warning(f"Image file not found: {self.image_path}")
            return None
            
        if self._image_cache is None:
            try:
                self._image_cache = Image.open(self.image_path)
            except Exception as e:
                logger.error(f"Failed to load image {self.image_path}: {e}")
                return None
                
        return self._image_cache
    
    def get_image_base64(self) -> Optional[str]:
        """Get image as base64 string."""
        image = self.load_image()
        if not image:
            return None
            
        try:
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode()
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {e}")
            return None
    
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
    
    def get_full_text(self, *, include_figure_descriptions: bool = True, normalize: bool = True) -> str:
        """
        Backward compatibility method matching FactCheckInterface.
        
        Args:
            include_figure_descriptions: Whether to include figure placeholders
            normalize: Whether to normalize text (currently just strips)
            
        Returns:
            Document text with or without figure placeholders
        """
        if include_figure_descriptions:
            return self.get_content(output_format=OutputFormat.TEXT_WITH_PLACEHOLDERS)
        else:
            return self.get_text_only()
    
    def get_text_with_locations(self, *, normalize: bool = True) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Backward compatibility method matching FactCheckInterface.
        
        Returns:
            List of (text, metadata) tuples
        """
        items = self._get_content_items([ContentType.TEXT])
        results = []
        
        for item in items:
            if item.text:
                text = item.text.strip() if normalize else item.text
                metadata = {
                    "page_index": item.page_index,
                    "block_id": item.block.id,
                    "bbox": item.block.bbox,
                    "role": item.block.role
                }
                results.append((text, metadata))
        
        return results
    
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