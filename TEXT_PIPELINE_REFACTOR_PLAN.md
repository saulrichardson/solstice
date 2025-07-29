# Text Pipeline Refactor Plan

## Goal
Create a modular text processing pipeline that slots in after PyMuPDF extraction to fix spacing and other text issues before the text is stored in the Document.

## Current State
- PyMuPDF extracts text with spacing issues (e.g., "Thesehighlightsdonot")
- `final_spacing_fixer.py` contains all the logic to fix these issues
- No clear pipeline structure for text processing
- Fixes would need to be added directly to PyMuPDFExtractor

## Proposed Architecture

### 1. Create Modular Pipeline Structure
**File**: `src/injestion/processing/text_pipeline.py`

```python
from typing import Protocol
import logging

logger = logging.getLogger(__name__)

class TextProcessor(Protocol):
    """Protocol for text processors."""
    def process(self, text: str) -> str:
        """Process and return modified text."""
        ...

class TextPipeline:
    """Simple text processing pipeline."""
    def __init__(self):
        self.processors = [
            WordNinjaProcessor(),  # Contains all spacing fixes
        ]
    
    def process(self, text: str) -> str:
        """Run text through all processors."""
        for processor in self.processors:
            text = processor.process(text)
        return text

# Global instance for easy access
_pipeline = TextPipeline()

def process_text(text: str) -> str:
    """Process text through the pipeline."""
    return _pipeline.process(text)
```

### 2. Create WordNinja Processor
**Location**: Within `text_pipeline.py`

```python
class WordNinjaProcessor:
    """Fix spacing using WordNinja and heuristics."""
    def __init__(self):
        try:
            from .text_extractors.final_spacing_fixer import fix_pdf_text_spacing
            self._fix = fix_pdf_text_spacing
            self.available = True
        except ImportError:
            self._fix = lambda x: x  # no-op fallback
            self.available = False
            logger.warning("WordNinja not available - spacing fixes disabled")
    
    def process(self, text: str) -> str:
        return self._fix(text)
```

### 3. Integrate with PyMuPDFExtractor
**File**: `src/injestion/processing/text_extractors/pymupdf_extractor.py`

```python
from ..text_pipeline import process_text

class PyMuPDFExtractor(TextExtractor):
    def extract_text_from_bbox(self, ...):
        # Existing code
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        # ... coordinate conversion ...
        
        # Extract text
        text = page.get_text("text", clip=rect)
        text = text.strip()
        
        # NEW: Process through pipeline
        text = process_text(text)
        
        doc.close()
        
        return ExtractorResult(
            text=text,
            confidence=1.0,
            metadata={"method": "pymupdf", "scale_factor": scale_factor}
        )
```

## Implementation Steps

### Step 1: Install Dependencies
```bash
pip install wordninja
```
Add to `requirements.txt`:
```
wordninja>=2.0.0
```

### Step 2: Create Pipeline Infrastructure
1. Create `src/injestion/processing/text_pipeline.py`
2. Implement `TextProcessor` protocol
3. Implement `WordNinjaProcessor` 
4. Create `TextPipeline` class
5. Export `process_text()` function

### Step 3: Update PyMuPDFExtractor
1. Import `process_text` function
2. Add single line after text extraction: `text = process_text(text)`
3. No other changes needed

### Step 4: Testing
1. Create `test_text_pipeline.py`:
   - Test WordNinjaProcessor with known issues
   - Test pipeline with multiple processors
   - Test fallback when WordNinja unavailable

2. Test with real PDFs:
   - Run on FlublokPI.pdf
   - Verify "Thesehighlightsdonot" → "These highlights do not"
   - Check other known spacing issues

### Step 5: Validation
1. Run existing ingestion on test PDFs
2. Compare output before/after
3. Verify LLM sees improved text
4. Check performance impact (should be <5ms per block)

## Benefits of This Approach

1. **Minimal Changes** - Only 1 line change in PyMuPDFExtractor
2. **Reuses Existing Code** - All fixes in `final_spacing_fixer.py` are preserved
3. **Extensible** - Easy to add more processors later
4. **Testable** - Each processor can be tested independently
5. **No Configuration** - Works out of the box with sensible defaults

## Future Extensibility

If needed, we can easily add more processors:
```python
class TextPipeline:
    def __init__(self):
        self.processors = [
            WordNinjaProcessor(),      # Spacing fixes
            AcronymNormalizer(),       # Future: FDA → F.D.A.
            DateNormalizer(),          # Future: standardize dates
            ChemicalFormulaFixer(),    # Future: fix chemical formulas
        ]
```

## Rollback Plan

If issues arise:
1. Remove `process_text()` call from PyMuPDFExtractor
2. Text extraction returns to original behavior
3. No other components affected

## Success Criteria

1. ✓ Text with spacing issues is automatically fixed
2. ✓ All existing functionality preserved
3. ✓ No performance degradation (<5ms per block)
4. ✓ LLM receives properly formatted text
5. ✓ Easy to extend with new processors