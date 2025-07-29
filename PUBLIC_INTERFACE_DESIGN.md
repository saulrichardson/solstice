# Public Document Interface Design

## Current Problem
- `FactCheckInterface` is in ingestion package but used by fact_check
- This creates unnecessary coupling between packages

## Better Solution: Public Interface Package

### Create `src/interfaces/` or `src/common/`

```
src/
├── interfaces/          # Public contracts between packages
│   ├── __init__.py
│   ├── document.py      # Document data model
│   └── readers.py       # Document reader interfaces
├── injestion/          # Produces documents
├── fact_check/         # Consumes documents
└── gateway/            # Independent service
```

### 1. Public Document Model
```python
# src/interfaces/document.py
"""Public document interface used across the system."""

from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field

class Block(BaseModel):
    """A content block in the document."""
    id: str
    page_index: int
    role: str  # 'Text', 'Title', 'Figure', 'Table', etc.
    bbox: Tuple[float, float, float, float]
    text: Optional[str] = None
    image_path: Optional[str] = None  # For figures/tables
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Document(BaseModel):
    """Processed document with structured content."""
    source: str  # Original file path/URI
    blocks: List[Block]
    reading_order: List[List[str]]  # Block IDs per page
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def save(self, path: str) -> None:
        """Save document to JSON file."""
        ...
    
    @classmethod
    def load(cls, path: str) -> 'Document':
        """Load document from JSON file."""
        ...
```

### 2. Document Reader Interface
```python
# src/interfaces/readers.py
"""Standard readers for document consumption."""

from typing import Protocol, List, Tuple, Dict, Any
from .document import Document

class DocumentReader(Protocol):
    """Protocol for reading document content."""
    
    def get_full_text(self, include_figures: bool = True) -> str:
        """Get document as plain text."""
        ...
    
    def get_text_with_locations(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get text blocks with location metadata."""
        ...
    
    def get_page_text(self, page_index: int) -> str:
        """Get text for a specific page."""
        ...

class StandardDocumentReader:
    """Standard implementation of DocumentReader."""
    
    def __init__(self, document: Document):
        self.document = document
    
    def get_full_text(self, include_figures: bool = True) -> str:
        # Implementation here
        ...
```

### 3. Package Updates

**Ingestion** produces documents:
```python
# src/injestion/pipeline.py
from src.interfaces.document import Document, Block

def ingest_pdf(pdf_path: str) -> Document:
    # Process PDF...
    return Document(
        source=pdf_path,
        blocks=blocks,
        reading_order=reading_order
    )
```

**Fact Check** consumes documents:
```python
# src/fact_check/agents/supporting_evidence.py
from src.interfaces.document import Document
from src.interfaces.readers import StandardDocumentReader

def extract_evidence(document: Document):
    reader = StandardDocumentReader(document)
    text = reader.get_full_text()
    # Process text...
```

## Benefits

1. **True Decoupling**: Neither package depends on the other
2. **Stable Interface**: Changes to ingestion internals don't affect consumers
3. **Multiple Consumers**: Any new package can use documents
4. **Extensibility**: Can add new reader implementations
5. **Clear Contracts**: Public API is explicit

## Migration Plan

1. Create `src/interfaces/` package
2. Move `Document` and `Block` models there
3. Create `StandardDocumentReader` (based on current FactCheckInterface)
4. Update imports in both packages
5. Delete `fact_check_interface.py` from ingestion

This creates a proper **public API** that happens to be used by fact_check, rather than a fact_check-specific interface living in the wrong package.