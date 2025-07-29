# Flexible Document Reader Design

## Current Limitations
The current `FactCheckInterface` only provides:
- `get_full_text()` - Text with OR without figure placeholders
- `get_text_with_locations()` - Text blocks with metadata

## Enhanced Reader Interface

```python
# src/interfaces/readers.py

from enum import Enum
from typing import List, Dict, Any, Union
from abc import ABC, abstractmethod
from .document import Document, Block

class ContentType(Enum):
    """Types of content that can be extracted."""
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    ALL = "all"

class OutputFormat(Enum):
    """Output format options."""
    TEXT_ONLY = "text_only"              # Pure text, no placeholders
    TEXT_WITH_PLACEHOLDERS = "placeholders"  # Text with [FIGURE 1] markers
    MIXED_CONTENT = "mixed"              # Text + actual images/tables
    STRUCTURED = "structured"            # List of content items with types

class DocumentReader(ABC):
    """Enhanced reader with flexible content extraction."""
    
    @abstractmethod
    def get_content(
        self,
        content_types: List[ContentType] = [ContentType.ALL],
        output_format: OutputFormat = OutputFormat.TEXT_WITH_PLACEHOLDERS,
        page_range: tuple[int, int] | None = None
    ) -> Union[str, List[Dict[str, Any]]]:
        """
        Get document content with flexible options.
        
        Args:
            content_types: Which types to include
            output_format: How to format the output
            page_range: Optional (start, end) pages
            
        Returns:
            String or structured list depending on format
        """
        pass
    
    # Convenience methods
    @abstractmethod
    def get_text_only(self) -> str:
        """Get pure text without any placeholders."""
        pass
    
    @abstractmethod
    def get_figures_only(self) -> List[Dict[str, Any]]:
        """Get list of figures with paths and metadata."""
        pass
    
    @abstractmethod
    def get_structured_content(self) -> List[Dict[str, Any]]:
        """Get all content in reading order with types."""
        pass

class StandardDocumentReader(DocumentReader):
    """Standard implementation with all options."""
    
    def __init__(self, document: Document):
        self.document = document
    
    def get_content(
        self,
        content_types: List[ContentType] = [ContentType.ALL],
        output_format: OutputFormat = OutputFormat.TEXT_WITH_PLACEHOLDERS,
        page_range: tuple[int, int] | None = None
    ) -> Union[str, List[Dict[str, Any]]]:
        """Flexible content extraction."""
        
        # Get blocks in reading order
        blocks_in_order = self._get_blocks_in_order(page_range)
        
        # Filter by content type
        filtered_blocks = self._filter_by_type(blocks_in_order, content_types)
        
        # Format output
        if output_format == OutputFormat.TEXT_ONLY:
            return self._format_text_only(filtered_blocks)
        elif output_format == OutputFormat.TEXT_WITH_PLACEHOLDERS:
            return self._format_with_placeholders(filtered_blocks)
        elif output_format == OutputFormat.MIXED_CONTENT:
            return self._format_mixed_content(filtered_blocks)
        else:  # STRUCTURED
            return self._format_structured(filtered_blocks)
    
    def get_text_only(self) -> str:
        """Pure text, no placeholders."""
        return self.get_content(
            content_types=[ContentType.TEXT],
            output_format=OutputFormat.TEXT_ONLY
        )
    
    def get_figures_only(self) -> List[Dict[str, Any]]:
        """Just the figures with metadata."""
        blocks = self.get_content(
            content_types=[ContentType.FIGURE],
            output_format=OutputFormat.STRUCTURED
        )
        return blocks
    
    def get_structured_content(self) -> List[Dict[str, Any]]:
        """Everything in reading order."""
        return self.get_content(
            content_types=[ContentType.ALL],
            output_format=OutputFormat.STRUCTURED
        )
    
    def _format_structured(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        """Format as structured list."""
        result = []
        for block in blocks:
            item = {
                "id": block.id,
                "type": block.role.lower(),
                "page": block.page_index,
                "bbox": block.bbox,
            }
            
            if block.text:
                item["content"] = block.text
            if block.image_path:
                item["image_path"] = block.image_path
                # Could also load image and include as base64
                
            result.append(item)
        return result
```

## Usage Examples

```python
# Create reader
reader = StandardDocumentReader(document)

# 1. Pure text (no placeholders)
text = reader.get_text_only()
# "This is the document text without any figure markers"

# 2. Text with placeholders (current behavior)
text_with_placeholders = reader.get_content()
# "This is text... [FIGURE 1 - See figure_p1_123.png] ... more text"

# 3. Just figures in order
figures = reader.get_figures_only()
# [
#   {"id": "123", "type": "figure", "page": 0, "image_path": "figures/fig1.png"},
#   {"id": "456", "type": "table", "page": 1, "image_path": "figures/table1.png"}
# ]

# 4. Everything structured (for custom rendering)
all_content = reader.get_structured_content()
# [
#   {"id": "1", "type": "text", "content": "Introduction..."},
#   {"id": "2", "type": "figure", "image_path": "figures/fig1.png"},
#   {"id": "3", "type": "text", "content": "As shown above..."},
#   {"id": "4", "type": "table", "image_path": "figures/table1.png"}
# ]

# 5. Specific pages only
page_2_content = reader.get_content(
    page_range=(2, 3),  # Just page 2
    output_format=OutputFormat.STRUCTURED
)

# 6. Mixed content (for rich display)
mixed = reader.get_content(
    output_format=OutputFormat.MIXED_CONTENT
)
# Returns dict with text and embedded image data
```

## Benefits

1. **Flexible Extraction**: Get exactly what you need
2. **Preserves Order**: Everything in reading order
3. **Multiple Formats**: String or structured data
4. **Extensible**: Easy to add new output formats
5. **Backwards Compatible**: Can provide same interface as current

## For Different Use Cases

- **Fact Checking**: Use `get_text_only()` or with placeholders
- **Display/Preview**: Use `get_structured_content()` for rich rendering  
- **Analysis**: Use `get_figures_only()` for image analysis
- **Export**: Use `get_content()` with custom formatting
- **LLM Context**: Choose format based on model capabilities

This design gives consumers complete control over what they get and how it's formatted!