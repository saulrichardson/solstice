# Processing Module

Core document processing components for layout analysis, text extraction, and content structuring.

## Overview

The processing module contains the core algorithms and services for transforming raw PDFs into structured documents:
- **Layout Detection**: Deep learning-based document structure analysis
- **Text Extraction**: Multi-strategy text retrieval with quality enhancement
- **Box Management**: Spatial operations on detected regions
- **Reading Order**: Logical flow determination
- **Text Processing**: Intelligent text cleaning and correction

## Components

### box.py
Fundamental data structure for layout regions:

```python
from src.injestion.shared.processing.box import Box

box = Box(
    x1=100, y1=200, x2=300, y2=400,
    text="Content here",
    type="Text",
    confidence=0.95
)

# Spatial operations
area = box.area
iou = box.intersection_over_union(other_box)
merged = Box.merge_boxes([box1, box2])
```

### layout_detector.py
**Note: Moved to `src/injestion/scientific/processing/layout_detector.py`** - only used by scientific pipeline.

Detectron2-based layout analysis pipeline:

```python
from src.injestion.scientific.processing.layout_detector import LayoutDetectionPipeline

detector = LayoutDetectionPipeline(
    config_path="PubLayNet/faster_rcnn",
    confidence_threshold=0.8
)

boxes = detector.detect(image_path)
```

**Features:**
- Multiple model support (PubLayNet, PrimaLayout)
- Configurable confidence thresholds
- GPU acceleration when available
- Batch processing support

### text_extractor.py
Intelligent text extraction with multiple strategies:

```python
from src.injestion.shared.processing.text_extractor import extract_document_content

document = extract_document_content(
    pdf_path="document.pdf",
    layout_boxes=detected_boxes,
    apply_text_processing=True
)
```

**Extraction Strategies:**
1. Native PDF text (PyMuPDF)
2. OCR fallback (future)
3. Table structure preservation
4. Figure caption extraction

### text_processing.py
Simple text cleaning and enhancement:

```python
from src.injestion.shared.processing.text_processing import process_text_simple

# Fix spacing issues
text = "Patientdatashowsimprovement"
fixed = process_text_simple(text)
# Output: "Patient data shows improvement"

# Preserve medical terms
text = "Flublok® prevents COVID-19"
fixed = process_text_simple(text)
# Output: "Flublok® prevents COVID-19" (unchanged)
```

**Processing Steps (in order):**
1. **Post-extraction Cleaning**: Fixes PDF artifacts, truncated words, ligatures
2. **WordNinja Spacing**: Intelligent word segmentation for concatenated text (must run before SymSpell)
3. **SymSpell Correction** (optional): Spell-checking and compound word splitting
4. **Whitespace Cleanup**: Consistent spacing and formatting

### overlap_resolver.py
**Note: Moved to `src/injestion/scientific/processing/overlap_resolver.py`** - only used by scientific pipeline.

Resolves conflicts between detected regions:

```python
from src.injestion.scientific.processing.overlap_resolver import no_overlap_pipeline

# Remove overlapping boxes
clean_boxes = no_overlap_pipeline(
    raw_boxes,
    merge_threshold=0.3,
    confidence_weight=0.7
)
```

**Resolution Strategies:**
- Remove different-type overlaps (keep highest confidence)
- Merge same-type overlaps (IoU > threshold)
- Expand boxes to prevent text cutoffs
- Preserve visual element integrity

### reading_order.py
**Note: Moved to `src/injestion/scientific/processing/reading_order.py`** - only used by scientific pipeline.

Determines logical document flow:

```python
from src.injestion.scientific.processing.reading_order import determine_reading_order_simple

ordered_boxes = determine_reading_order_simple(boxes)
# Returns boxes sorted by reading order
```

**Algorithm:**
- Top-to-bottom, left-to-right ordering
- Handles basic column layouts
- Suitable for most document types
- **Hybrid**: Column-aware with section detection
- **Graph-based**: Future enhancement

### document_formatter.py
Converts processed data to various output formats:

```python
from src.injestion.shared.processing.document_formatter import DocumentFormatter

formatter = DocumentFormatter(document)

# Multiple output formats
text = formatter.to_text()
markdown = formatter.to_markdown()
html = formatter.to_html()
```

## Text Extractors Submodule

### base_extractor.py
Abstract interface for text extraction strategies:

```python
from src.injestion.shared.processing.text_extractors.base_extractor import BaseTextExtractor

class MyExtractor(BaseTextExtractor):
    def extract_text(self, box: Box, page) -> str:
        # Implementation
        pass
```

### pymupdf_extractor.py
Primary text extraction using PyMuPDF:
- Direct text extraction from PDF
- Preserves formatting information
- Handles Unicode properly
- Fast and memory efficient

### symspell_corrector_optimized.py
Spell correction for OCR output:
- SymSpell algorithm for fast correction
- Medical dictionary support
- Configurable edit distance
- Batch processing optimization

### post_extraction_cleaner.py
Post-processing cleanup:
- Remove artifacts
- Fix encoding issues
- Normalize whitespace
- Handle special characters

### final_spacing_fixer.py
Final pass for spacing issues:
- Sentence boundary detection
- Proper capitalization
- Paragraph separation
- List formatting

### noop_consolidator.py
**Note: Moved to `src/injestion/scientific/processing/noop_consolidator.py`** - only used by scientific pipeline.

No-operation consolidator for pipelines that don't need box merging:

```python
from src.injestion.scientific.processing.noop_consolidator import NoOpConsolidator

# Used by scientific pipeline for functional consolidation
consolidator = NoOpConsolidator()
boxes = consolidator.consolidate(raw_boxes)  # Returns unchanged
```

**Purpose**: Provides a null object pattern implementation for pipelines (like scientific) that use functional consolidation instead of complex merging.

## Usage Patterns

### Complete Pipeline
```python
# 1. Detect layout
detector = LayoutDetectionPipeline()
raw_boxes = detector.detect(page_image)

# 2. Resolve overlaps
clean_boxes = no_overlap_pipeline(raw_boxes)

# 3. Extract text
document = extract_document_content(
    pdf_path, 
    clean_boxes,
    apply_text_processing=True
)

# 4. Determine reading order (scientific pipeline only)
ordered_content = determine_reading_order_simple(document.blocks)
```

### Custom Text Processing
```python
# Simple function-based processing
from src.injestion.shared.processing.text_processing import process_text

result = process_text(text, context={'preserve_medical_terms': True})
processed_text = result.text
modifications = result.modifications  # Which processors modified the text

# Process document
for block in document.blocks:
    if block.is_text:
        block.text = service.process_text(block.text)
```

## Performance Optimization

### Layout Detection
- Use GPU when available (`CUDA_VISIBLE_DEVICES=0`)
- Batch multiple pages together
- Lower confidence threshold for speed
- Cache model weights locally

### Text Processing
- Process in parallel for multi-page docs
- Pre-compile regex patterns
- Use memory mapping for large PDFs
- Disable processing for known-good PDFs

## Configuration

### Processing Flags
```python
# In pipeline configuration
APPLY_TEXT_PROCESSING = True
MERGE_OVERLAPPING = True
EXPAND_BOXES = True
BOX_PADDING = 20.0
```

## Extending the Module

### Adding New Text Extractors
1. Inherit from `BaseTextExtractor`
2. Implement `extract_text()` method
3. Register in `text_extractor.py`

### Adding New Processing Steps
1. Create new processor function in `text_extractors/`
2. Add function to processor list in `text_processing.py`
3. Test the new pipeline

### Custom Layout Models
1. Train Detectron2 model
2. Export model weights
3. Update configuration paths
4. Test on sample documents