# Ingestion Module

Advanced PDF processing with two specialized pipelines for different document types.

## Overview

The ingestion module provides two distinct processing pipelines:

1. **Default Pipeline** (Scientific/Clinical PDFs): Standard processing with layout detection
2. **Marketing Pipeline** (Marketing Materials): Specialized processing in the `marketing/` subfolder

Both pipelines share common utilities in `processing/`, `storage/`, and `visualization/`.

## Folder Structure

```
injestion/
├── marketing/          # Complete pipeline for Flublok marketing PDFs
│   ├── detector.py    # PrimaLayout-based detection
│   ├── pipeline.py    # Marketing-specific orchestration
│   └── ...           # Other marketing-specific components
│
├── processing/        # Shared processing utilities
│   ├── text_processing_service.py
│   ├── layout_detector.py
│   └── ...
│
├── storage/          # Shared storage utilities
└── visualization/    # Shared visualization tools
```

## Default Pipeline (Scientific/Clinical Documents)

Used by `python -m src.cli ingest` for processing scientific PDFs:

```
PDF Input
    │
    ├─► Page Rasterization (400 DPI)
    │        │
    │        └─► Layout Detection (Detectron2/LayoutParser)
    │                 │
    │                 ├─► Box Detection (Text, Figure, Table, etc.)
    │                 │
    │                 └─► Overlap Resolution & Box Expansion
    │
    └─► Text Extraction (PyMuPDF)
             │
             ├─► Text Processing Service
             │    ├─► Post-extraction Cleaning (PDF artifacts)
             │    ├─► WordNinja Spacing Fixes
             │    └─► SymSpell Correction (optional)
             │
             └─► Content Assembly
                      │
                      └─► Structured Document Output
```

## Core Components

### Main Pipeline (`pipeline.py`)

The orchestration layer that coordinates all processing steps:

```python
from src.injestion.pipeline import PDFIngestionPipeline

# Process a PDF
pipeline = PDFIngestionPipeline()
document = pipeline.process_pdf(
    pdf_path="clinical_study.pdf",
    output_dir="data/cache"
)
```

**Key Features:**
- High-resolution processing (400 DPI)
- Automatic overlap resolution
- Text cutoff prevention
- Reading order detection

### Processing Submodules

#### `processing/layout_detector.py`
- Detectron2-based layout analysis
- PubLayNet model for academic documents
- Configurable confidence thresholds

#### `processing/text_extractor.py`
- PyMuPDF-based text extraction
- Falls back to OCR when needed
- Preserves formatting and structure

#### `processing/text_processing_service.py`
- Intelligent text cleaning and enhancement
- WordNinja for spacing correction
- Medical terminology preservation
- Configurable processing levels

#### `processing/overlap_resolver.py`
- Resolves overlapping layout boxes
- Merges fragmented text regions
- Preserves visual elements

#### `processing/reading_order.py`
- Determines logical reading flow
- Column detection
- Header/footer identification

### Storage (`storage/`)

Standardized file organization:
```
data/cache/<PDF_NAME>/
├── pages/                  # Rasterized page images
├── raw_layouts/           # Initial detection results
├── merged/                # Post-processing layouts
├── reading_order/         # Reading flow analysis
├── extracted/             # Final extracted content
│   ├── content.json      # Structured document
│   ├── document.txt      # Plain text
│   ├── document.md       # Markdown format
│   └── figures/          # Extracted images
└── visualizations/        # Debug visualizations
```

### Visualization (`visualization/`)

Quality assurance and debugging tools:
- Page layout visualizations
- Box overlap debugging
- Reading order flow diagrams

## Usage

### Default Pipeline (Scientific PDFs)

```python
# Using the CLI
python -m src.cli ingest

# Or programmatically
from src.injestion.pipeline import PDFIngestionPipeline

pipeline = PDFIngestionPipeline()
document = pipeline.process_pdf("document.pdf")

# Access structured content
for block in document.blocks:
    if block.is_text:
        print(f"Text: {block.text}")
    elif block.role == "Figure":
        print(f"Figure at: {block.image_path}")
```

### Marketing Pipeline (Flublok Marketing Materials)

```bash
# For marketing PDFs, use the specialized pipeline
python -m src.injestion.marketing.cli path/to/marketing.pdf

# With options
python -m src.injestion.marketing.cli marketing.pdf --preset aggressive
```

The marketing pipeline uses PrimaLayout (better for marketing layouts) instead of PubLayNet.

### Advanced Configuration

```python
# Custom settings
pipeline = PDFIngestionPipeline(
    detection_dpi=600,           # Higher quality
    merge_threshold=0.2,         # More aggressive merging
    confidence_threshold=0.8,    # Higher confidence required
    expand_boxes=True,           # Fix text cutoffs
    box_padding=30              # More padding
)
```

### Text Processing Options

```python
from src.injestion.processing.text_processing_service import TextProcessingService

# Configure text processing
service = TextProcessingService(
    fix_spacing=True,           # Apply WordNinja
    normalize_punctuation=True,  # Smart quotes, etc.
    preserve_medical_terms=True  # Keep medical terminology
)

# Process text
cleaned = service.process_text("Thisisatest.")
# Output: "This is a test."
```

## Key Features

### 1. Layout Detection
- Uses pre-trained Detectron2 models
- Detects: Text, Title, List, Figure, Table
- Confidence scoring for each detection
- Non-maximum suppression for clean results

### 2. Text Quality Enhancement
- **Spacing Fixes**: "patientdata" → "patient data"
- **Punctuation**: Smart quotes, proper dashes
- **Preservation**: Keeps "Flublok®", "COVID-19"
- **Context Aware**: Medical terms remain intact

### 3. Overlap Resolution
- Removes conflicting detections
- Merges fragmented text blocks
- Preserves highest-confidence regions
- Expands boxes to capture full content

### 4. Output Formats
- **JSON**: Structured document model
- **Text**: Plain text with reading order
- **Markdown**: Formatted with headers
- **HTML**: Tables and structure preserved

## Performance Considerations

### Memory Usage
- 400 DPI processing requires ~2GB per 10 pages
- Layout detection peaks at ~4GB for large PDFs
- Consider batch processing for documents >50 pages

### Processing Time
- ~5-10 seconds per page (layout detection)
- ~1-2 seconds per page (text extraction)
- Parallel processing available for multi-page docs

### Optimization Tips
1. Lower DPI for draft processing (200-300)
2. Disable visualizations in production
3. Use SSD storage for temp files
4. Process PDFs in batches of 10-20 pages

## Troubleshooting

### Common Issues

1. **"Config file does not exist"**
   - Clear cache: `rm -rf ~/.torch/iopath_cache/`
   - Reinstall: `make install-detectron2`

2. **Text cutoffs**
   - Increase `box_padding` (default: 20)
   - Enable `expand_boxes` (default: True)

3. **Poor text quality**
   - Check PDF has embedded text (not scanned)
   - Increase detection DPI
   - Verify text processing is enabled

4. **Memory errors**
   - Process in smaller batches
   - Reduce detection DPI
   - Increase system swap space

## Future Enhancements

- **OCR Integration**: For scanned documents
- **Table Extraction**: Structured table data
- **Multi-Column**: Better column detection
- **Language Support**: Non-English documents
- **Streaming**: Process without full PDF load
- **GPU Acceleration**: Faster layout detection