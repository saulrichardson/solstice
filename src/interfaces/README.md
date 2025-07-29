# Interfaces Module

Shared data models and type definitions for document processing in Solstice.

## Overview

The interfaces module defines the core data structures used throughout the Solstice pipeline. It provides:
- **Document Models**: Structured representation of processed documents
- **Content Types**: Enumerations for content classification
- **Reader Interfaces**: Standard interfaces for document readers

## Core Components

### document.py

Defines the document data model hierarchy:

```python
from src.interfaces.document import Document, Block, DocumentMetadata

# Document structure
document = Document(
    blocks=[...],       # List of content blocks
    metadata={...}      # Document-level metadata
)

# Individual blocks
text_block = Block(
    id="block_001",
    page_index=0,
    role="Text",
    bbox=(100, 200, 300, 400),  # x1, y1, x2, y2
    text="Content here..."
)
```

**Key Classes:**
- `Document`: Top-level container with blocks, reading order, and metadata
- `Block`: Individual content unit (text, figure, table) with bbox and role
- Reading order tracked per page as list of block IDs

### content_types.py

Type definitions and enumerations:

```python
from src.interfaces.content_types import ContentType, OutputFormat, BlockRole

# Content filtering
content_type = ContentType.TEXT  # or FIGURE, TABLE, ALL

# Output formatting
format = OutputFormat.TEXT_WITH_PLACEHOLDERS  # or TEXT_ONLY, STRUCTURED, VISION_READY

# Block classification
role = BlockRole.FIGURE  # or TEXT, TITLE, LIST, TABLE
```

### readers.py

Abstract interfaces for document readers:

```python
from src.interfaces.readers import BaseDocumentReader

class MyReader(BaseDocumentReader):
    def read_document(self, path: Path) -> Document:
        # Implementation
        pass
```

## Usage Examples

### Creating a Document

```python
from src.interfaces.document import Document, Block
from src.interfaces.content_types import BlockRole

# Create blocks
title = Block(
    id="title_1",
    page_index=0,
    role=BlockRole.TITLE.value,
    bbox=(50, 50, 500, 100),
    text="Document Title"
)

paragraph = Block(
    id="para_1", 
    page_index=0,
    role=BlockRole.TEXT.value,
    bbox=(50, 120, 500, 300),
    text="This is a paragraph..."
)

# Create document
doc = Document(
    blocks=[title, paragraph],
    metadata={"source": "example.pdf", "pages": 1}
)
```

### Filtering Content

```python
# Get only text blocks
text_blocks = [b for b in doc.blocks if b.is_text]

# Get figures and tables
visual_blocks = [b for b in doc.blocks if b.is_visual]

# Get content from specific page
page_1_blocks = [b for b in doc.blocks if b.page_index == 0]
```

### Working with Document Content

```python
from src.interfaces.document import Document

# Access all blocks
for block in doc.blocks:
    if block.is_text:
        print(block.text)
    elif block.is_visual:
        print(f"Visual content at: {block.image_path}")

# Get reading order for a page
page_0_order = doc.reading_order[0]  # List of block IDs in order

# Save/load documents
doc.save("output.json")
loaded_doc = Document.load("output.json")
```

## Block Types

### Text Blocks
- **Role**: "Text", "Title", "List"
- **Content**: `text` field populated
- **Usage**: Regular document text, headings, bullet points

### Figure Blocks
- **Role**: "Figure"
- **Content**: `image_path` field with relative path
- **Usage**: Charts, diagrams, photos

### Table Blocks
- **Role**: "Table"
- **Content**: `html` field with table markup (legacy) or `image_path`
- **Usage**: Structured tabular data

## Design Principles

1. **Immutability**: Use Pydantic models for validation and immutability
2. **Type Safety**: Strong typing with enums and type hints
3. **Extensibility**: Metadata fields for custom attributes
4. **Simplicity**: Clear, focused interfaces

## Integration Points

### With Ingestion Pipeline
```python
# Ingestion creates Document objects
document = pipeline.process_pdf("input.pdf")
```

### With Fact Checking
```python
# Fact checker consumes Document objects
evidence = fact_checker.find_evidence(document, claim)
```

### With Gateway
```python
# Gateway serializes for API responses
response = document.model_dump()
```

## Future Enhancements

- **Block Relationships**: Parent-child hierarchies for nested content
- **Confidence Scores**: Detection confidence per block
- **Language Detection**: Per-block language identification
- **Layout Preservation**: Column and section information
- **Semantic Roles**: More granular content classification