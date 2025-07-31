# Interfaces Module

Shared data models and type definitions for document processing in Solstice.

## Architecture Overview

The interfaces module serves as the contract layer for the entire Solstice system, defining the data structures that flow between components. It ensures type safety, data consistency, and clear boundaries between modules through well-defined interfaces.

### Key Responsibilities

- **Document Models**: Pydantic-based models for structured document representation
- **Content Types**: Type-safe enumerations for content classification
- **Data Validation**: Automatic validation of data structures
- **Serialization**: JSON-compatible models for persistence and API communication
- **Reader Interfaces**: Abstract base classes for extensible document readers
- **Type Safety**: Strong typing throughout the system

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

## Architecture Principles

1. **Immutability**: Pydantic models provide validation and encourage immutable data
2. **Type Safety**: Comprehensive type hints and enums prevent runtime errors
3. **Extensibility**: Metadata fields allow custom attributes without schema changes
4. **Simplicity**: Clear, focused interfaces with single responsibilities
5. **Validation**: Automatic validation on construction ensures data integrity
6. **Serialization**: Native JSON support for all models

## Data Flow Architecture

```
PDF Input
    │
    ├─► Ingestion Pipeline
    │       │
    │       └─► Creates Document + Blocks
    │                    │
    ├─────────────────► Fact Checking
    │                    │ (consumes Document)
    │                    │
    └─────────────────► Gateway API
                         │ (serializes Document)
                         │
                         └─► JSON Response
```

## Model Relationships

### Document Hierarchy
```
Document
├── blocks: List[Block]
│   ├── Block (Text)
│   ├── Block (Title)
│   ├── Block (Figure)
│   └── Block (Table)
├── reading_order: List[List[str]]
│   └── Per-page block ID sequences
└── metadata: Dict[str, Any]
    └── Custom attributes
```

### Block Properties
- **Identity**: Unique ID and page location
- **Spatial**: Bounding box coordinates
- **Content**: Text, HTML, or image path
- **Classification**: Role-based typing
- **Metadata**: Extensible attributes

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

## Performance Considerations

### Memory Efficiency
- Blocks store only relevant content (text OR image_path)
- Metadata lazy-loaded when needed
- Efficient serialization with Pydantic

### Validation Performance
- Validation occurs once at construction
- Type checking at development time (mypy)
- No runtime overhead after creation

## Best Practices

### Creating Documents
```python
# Good: Use Document model with validation
blocks = []
for page in pages:
    for region in page.regions:
        block = Block(
            id=f"block_{region.id}",
            page_index=page.index,
            role=region.type,
            bbox=region.bbox,
            text=region.text
        )
        blocks.append(block)
document = Document(blocks=blocks, metadata={})

# Bad: Manual construction without validation
document = {"blocks": [...]}  # No type safety!
```

### Working with Blocks
```python
# Good: Use properties for type checking
if block.is_text:
    process_text(block.text)
elif block.is_visual:
    process_image(block.image_path)

# Good: Use metadata for extensions
block.metadata["confidence"] = 0.95
block.metadata["language"] = "en"
```

## Future Enhancements

1. **Block Relationships**: Parent-child hierarchies for nested content
2. **Confidence Scores**: Detection confidence as first-class property
3. **Language Detection**: Per-block language identification
4. **Layout Preservation**: Column, section, and page layout info
5. **Semantic Roles**: More granular content classification (e.g., "caption", "footnote")
6. **Version Control**: Document versioning and diff support
7. **Streaming Support**: Lazy loading for large documents
8. **Graph Representation**: Blocks as nodes with relationships