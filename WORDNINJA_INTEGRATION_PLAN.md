# WordNinja Integration Plan for Text Processing Pipeline

## Current Architecture Understanding

The text extraction pipeline has these key components:

1. **Pipeline** (`src/injestion/pipeline.py`)
   - Main orchestration
   - Calls `extract_document_content()`

2. **Text Extractor** (`src/injestion/processing/text_extractor.py`)
   - `extract_document_content()` - Main function that processes all blocks
   - `get_text_extractor()` - Returns PyMuPDF or Paddle extractor
   - Extracts text at line 155: `block.text = result.text`

3. **PyMuPDF Extractor** (`src/injestion/processing/text_extractors/pymupdf_extractor.py`)
   - Returns `ExtractorResult` with extracted text
   - Currently returns raw text with spacing issues

## Integration Plan

### Option 1: Modify PyMuPDFExtractor (Recommended)
**Location**: `pymupdf_extractor.py`
**Changes**:
1. Add WordNinja import and initialization
2. Apply spacing fix in `extract_text_from_bbox()` before returning
3. Add configuration option to enable/disable

**Pros**:
- Clean integration at the source
- All PyMuPDF extractions get fixed automatically
- No changes needed elsewhere

**Cons**:
- Adds dependency to extractor

### Option 2: Add Post-Processing Step
**Location**: `text_extractor.py` at line 155
**Changes**:
1. After `result = get_text_extractor(...).extract_text_from_bbox(...)`
2. Apply WordNinja fix to `result.text`
3. Then assign to `block.text`

**Pros**:
- Centralized processing
- Works for all extractor types
- Easy to toggle on/off

**Cons**:
- Modifies core pipeline code

### Option 3: Create a Wrapper Extractor
**Location**: New file `pymupdf_wordninja_extractor.py`
**Changes**:
1. Inherit from PyMuPDFExtractor
2. Override `extract_text_from_bbox()` to add WordNinja
3. Register as new extractor type

**Pros**:
- No changes to existing code
- Optional usage
- Clean separation of concerns

**Cons**:
- Another extractor type to maintain

## Recommended Implementation Steps

1. **Install WordNinja**
   ```bash
   pip install wordninja
   ```

2. **Implement Option 1** - Modify PyMuPDFExtractor:
   - Add WordNinja import with fallback
   - Create spacing fix method
   - Apply fix before returning text
   - Add config option in settings

3. **Add Tests**
   - Test with known problematic PDFs
   - Verify spacing improvements
   - Check performance impact

4. **Update Configuration**
   - Add `fix_spacing` option to settings
   - Default to True for better text quality

5. **Document Changes**
   - Update README with WordNinja dependency
   - Document spacing fix behavior

## Code Changes Needed

### 1. Update `requirements.txt`
```
wordninja>=2.0.0
```

### 2. Modify `pymupdf_extractor.py`
- Import wordninja
- Add `_fix_text_spacing()` method
- Apply in `extract_text_from_bbox()`

### 3. Update `settings.py` (optional)
- Add `fix_text_spacing: bool = True`

## Performance Considerations

- WordNinja adds ~5ms per text block
- For 100 blocks: ~0.5s total overhead
- Minimal performance impact
- Acceptable tradeoff for better quality

## Testing Plan

1. Run existing tests to ensure no breakage
2. Add specific spacing fix tests
3. Compare LLM accuracy with/without fixes
4. Measure performance impact

## Rollout Strategy

1. Implement with feature flag (default on)
2. Test on sample documents
3. Monitor LLM response quality
4. Gather feedback
5. Remove flag once stable