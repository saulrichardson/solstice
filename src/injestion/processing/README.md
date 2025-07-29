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
from src.injestion.processing.box import Box

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
Detectron2-based layout analysis pipeline:

```python
from src.injestion.processing.layout_detector import LayoutDetectionPipeline

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
from src.injestion.processing.text_extractor import extract_document_content

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

### text_processing_service.py
Advanced text cleaning and enhancement:

```python
from src.injestion.processing.text_processing_service import TextProcessingService

service = TextProcessingService()

# Fix spacing issues
text = "Patientdatashowsimprovement"
fixed = service.process_text(text)
# Output: "Patient data shows improvement"

# Preserve medical terms
text = "Flublok® prevents COVID-19"
fixed = service.process_text(text)
# Output: "Flublok® prevents COVID-19" (unchanged)
```

**Processing Steps (in order):**
1. **Post-extraction Cleaning**: Fixes PDF artifacts, truncated words, ligatures
2. **WordNinja Spacing**: Intelligent word segmentation for concatenated text (must run before SymSpell)
3. **SymSpell Correction** (optional): Spell-checking and compound word splitting
4. **Whitespace Cleanup**: Consistent spacing and formatting

### overlap_resolver.py
Resolves conflicts between detected regions:

```python
from src.injestion.processing.overlap_resolver import no_overlap_pipeline

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

### reading_order.py & reading_order_hybrid.py
Determines logical document flow:

```python
from src.injestion.processing.reading_order import determine_reading_order_simple

ordered_boxes = determine_reading_order_simple(boxes)
# Returns boxes sorted by reading order
```

**Algorithms:**
- **Simple**: Top-to-bottom, left-to-right
- **Hybrid**: Column-aware with section detection
- **Graph-based**: Future enhancement

### document_formatter.py
Converts processed data to various output formats:

```python
from src.injestion.processing.document_formatter import DocumentFormatter

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
from src.injestion.processing.text_extractors.base_extractor import BaseTextExtractor

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

# 4. Determine reading order
ordered_content = determine_reading_order_simple(document.blocks)
```

### Custom Text Processing
```python
# Configure processing
service = TextProcessingService(
    fix_spacing=True,
    normalize_punctuation=True,
    min_word_length=2,
    preserve_patterns=[r"COVID-\d+", r"\w+®"]
)

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

### Environment Variables
```bash
# Layout detection
DETECTRON2_CONFIG="PubLayNet/faster_rcnn"
DETECTION_CONFIDENCE=0.8
DETECTION_NMS_THRESHOLD=0.5

# Text processing
TEXT_FIX_SPACING=true
TEXT_PRESERVE_MEDICAL=true
TEXT_NORMALIZE_PUNCT=true
```

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
1. Create new processor class
2. Implement `process()` method
3. Add to `TextProcessingService` pipeline

### Custom Layout Models
1. Train Detectron2 model
2. Export model weights
3. Update configuration paths
4. Test on sample documents