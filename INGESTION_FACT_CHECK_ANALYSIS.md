# Ingestion-FactCheck Separation Analysis

## Current State

### Ingestion Pipeline Output
The ingestion pipeline produces:
1. **Document Model** (`content.json`) - Structured data with:
   - Blocks with text, bbox, page info
   - Reading order per page
   - Metadata (scores, DPI, etc.)
   - Image paths for figures/tables

2. **Multiple Formats**:
   - `document.json` - Structured format
   - `document.txt` - Plain text
   - `document.md` - Markdown with images
   - `document.html` - HTML version
   - Extracted figures as PNG files

### Interface Between Packages

**Clean Interface**: `FactCheckInterface`
```python
# Only 2 imports from ingestion:
from src.injestion.models.document import Document
from src.injestion.processing.fact_check_interface import FactCheckInterface
```

The fact_check agents only interact with:
- `Document` model (data structure)
- `FactCheckInterface` (accessor methods)

### Are We Achieving Separation? ✅ YES

**Evidence of Good Separation:**

1. **Minimal Coupling**
   - Fact_check only imports 2 items from ingestion
   - No direct access to processing logic
   - Clean data model interface

2. **Self-Contained Processing**
   - Ingestion handles ALL text processing:
     - Layout detection
     - Text extraction
     - Spacing fixes (WordNinja)
     - Reading order
     - Figure/table extraction
   - Produces ready-to-consume output

3. **Standard Output Format**
   - Document model is simple and stable
   - Multiple output formats for different consumers
   - Fact_check agents get clean, processed text

4. **No Reverse Dependencies**
   - Ingestion doesn't import from fact_check
   - Pipeline runs independently

## What's Working Well

1. **Text Quality**: Text is fully processed with spacing fixes before fact_check sees it
2. **Location Tracking**: Each text block maintains its source location (page, bbox)
3. **Figure Handling**: Figures extracted as images with placeholders in text
4. **Reading Order**: Proper document flow preserved

## Potential Improvements

### 1. Move `FactCheckInterface` 
Currently in: `src/injestion/processing/fact_check_interface.py`
Should be in: `src/fact_check/interfaces/document_interface.py`

**Why?** The interface is really a fact_check concern, not an ingestion concern.

### 2. Create Abstract Interface
Instead of importing concrete `Document` class:
```python
# src/common/interfaces/document.py
class IDocument(Protocol):
    blocks: List[IBlock]
    reading_order: List[List[str]]
    # ... minimal interface
```

### 3. Package-Level Exports
Create cleaner imports:
```python
# src/injestion/__init__.py
from .models.document import Document
from .pipeline import ingest_pdf

__all__ = ['Document', 'ingest_pdf']
```

## Conclusion

The separation is **already quite good**:
- Ingestion is self-contained ✅
- Output is ready for agents ✅
- Interface is minimal ✅
- No circular dependencies ✅

The main improvement would be moving `FactCheckInterface` to the fact_check package since it's really a consumer concern, not a producer concern.