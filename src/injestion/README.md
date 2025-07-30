# Ingestion Module

PDF processing with layout detection and text extraction.

## Overview

The ingestion module provides PDF processing with layout detection and text extraction. Two pipelines:

1. **Scientific Pipeline** (`scientific/`): For academic papers and research documents
2. **Marketing Pipeline** (`marketing/`): For marketing materials with complex layouts

## Module Structure

```
injestion/
├── scientific/              # Main pipeline for academic/clinical documents
│   ├── __init__.py         # Exports: ingest_pdf, PDFIngestionPipeline
│   ├── pipeline.py         # High-level orchestration
│   └── standard_pipeline.py # StandardPipeline implementation
│
├── marketing/              # Specialized pipeline for marketing materials
│   ├── cli.py             # Command-line interface
│   ├── detector.py        # PrimaLayout-based detection
│   ├── pipeline.py        # MarketingPipeline implementation
│   ├── consolidation.py   # Advanced box merging for marketing layouts
│   └── reading_order.py   # Marketing-specific reading order
│
└── shared/                 # Common utilities used by both pipelines
    ├── base_pipeline.py   # Abstract base class for all pipelines
    ├── config.py          # Shared configuration settings
    ├── processing/        # Document processing components
    ├── storage/           # File I/O and path management
    └── visualization/     # Debug and quality assurance tools
```

## Pipeline Comparison

| Feature | Scientific Pipeline | Marketing Pipeline |
|---------|-------------------|-------------------|
| **Model** | PubLayNet | PrimaLayout |
| **Label IDs** | Start at 0 | Start at 1 |
| **Labels** | Text, Title, List, Table, Figure | TextRegion, ImageRegion, TableRegion, etc. |
| **Reading Order** | Hybrid algorithm | Marketing-specific |
| **Default Threshold** | 0.2 | 0.1 |

## Scientific Pipeline

### Architecture

```
PDF Document
    │
    ├─► Page Rasterization (400 DPI)
    │        │
    │        └─► Layout Detection (PubLayNet/Detectron2)
    │                 │
    │                 ├─► Box Detection with Labels:
    │                 │   - 0: Text
    │                 │   - 1: Title
    │                 │   - 2: List
    │                 │   - 3: Table
    │                 │   - 4: Figure
    │                 │
    │                 └─► Overlap Resolution & Box Expansion
    │
    └─► Text Extraction (PyMuPDF)
             │
             ├─► Text Processing Service
             │    ├─► PDF Artifact Removal
             │    ├─► WordNinja Spacing Correction
             │    └─► Medical Term Preservation
             │
             └─► Document Assembly
                      │
                      └─► Structured Output (JSON/MD/HTML)
```

### Usage

```python
# CLI usage
python -m src.cli ingest

# Programmatic usage
from src.injestion.scientific import ingest_pdf

document = ingest_pdf("research_paper.pdf")
print(f"Extracted {len(document.blocks)} blocks")
```

### Configuration

```python
from src.injestion.scientific import PDFIngestionPipeline
from src.injestion.shared.config import IngestionConfig

config = IngestionConfig(
    detection_dpi=600,              # Higher quality scanning
    score_threshold=0.3,            # Stricter confidence requirement
    merge_threshold=0.5,            # IOU threshold for same-type merging
    same_type_merge_threshold=0.8,  # Configurable overlap threshold
    expand_boxes=True,              # Prevent text cutoffs
    box_padding=20                  # Pixels to expand boxes
)

pipeline = PDFIngestionPipeline(config=config)
```

## Marketing Pipeline

### Architecture

```
Marketing PDF
    │
    ├─► Page Rasterization (configurable DPI)
    │        │
    │        └─► Layout Detection (PrimaLayout/Detectron2)
    │                 │
    │                 ├─► Box Detection with Labels:
    │                 │   - 1: TextRegion
    │                 │   - 2: ImageRegion
    │                 │   - 3: TableRegion
    │                 │   - 4: MathsRegion
    │                 │   - 5: SeparatorRegion
    │                 │   - 6: OtherRegion
    │                 │
    │                 └─► Advanced Box Consolidation
    │
    └─► Marketing-Optimized Processing
             │
             ├─► Logo Detection & Reclassification
             ├─► Multi-Column Handling
             └─► Feature-Based Reading Order
```

### Usage

```bash
# Process marketing PDF
python -m src.injestion.marketing.cli marketing_flyer.pdf

# With custom settings
python -m src.injestion.marketing.cli brochure.pdf \
    --merge-threshold 0.1 \
    --box-padding 15.0 \
    --preset aggressive
```

### Presets

- **aggressive**: Maximum consolidation (merge_threshold=0.05)
- **conservative**: Minimal merging (merge_threshold=0.5, expand_boxes=False)
- **marketing**: Optimized for marketing docs (score_threshold=0.15)

## Shared Components

### Text Processing Service

The `TextProcessingService` provides intelligent text correction:

```python
from src.injestion.shared.processing.text_processing_service import TextProcessingService

service = TextProcessingService(
    fix_spacing=True,               # "patientdata" → "patient data"
    normalize_punctuation=True,     # Smart quotes, proper dashes
    preserve_medical_terms=True,    # Keep "Flublok®", "COVID-19"
    min_word_length=3              # Minimum length for spacing fixes
)

cleaned = service.process_text("Thisisatest ofFlublok®vaccine.")
# Output: "This is a test of Flublok® vaccine."
```

### Overlap Resolution

The overlap resolver ensures no overlapping boxes in the final output:

```python
from src.injestion.shared.processing.overlap_resolver import no_overlap_pipeline

boxes = no_overlap_pipeline(
    detected_boxes,
    merge_same_type_first=True,
    merge_threshold=0.5,
    same_type_merge_threshold=0.8,  # Now configurable!
    minor_overlap_threshold=0.05
)
```

### Reading Order Detection

Two algorithms are available:

1. **Hybrid Algorithm** (`reading_order_hybrid.py`):
   - Uses k-means clustering for column detection
   - Builds DAG of reading dependencies
   - Handles spanning blocks (figures, tables)
   - Fixed: Now correctly checks horizontal overlap

2. **Simple Algorithm** (`reading_order.py`):
   - Top-to-bottom, left-to-right ordering
   - Fallback for single-column documents

## Output Structure

```
data/cache/<PDF_NAME>/
├── pages/                  # Rasterized page images (PNG)
├── raw_layouts/           # Initial detection results
│   └── raw_layout_boxes.json
├── merged/                # Post-consolidation layouts
│   └── merged_boxes.json
├── reading_order/         # Reading flow analysis
│   └── reading_order.json
├── extracted/             # Final outputs
│   ├── content.json      # Structured document (Document object)
│   ├── document.txt      # Plain text with reading order
│   ├── document.md       # Markdown with formatting
│   ├── document.html     # HTML with tables
│   └── figures/          # Extracted images (PNG)
└── visualizations/        # Debug visualizations
    ├── page_*_layout.png # Per-page layout boxes
    └── all_pages_summary.png
```

## Performance & Optimization

### Resource Requirements

| Document Size | RAM Usage | Processing Time |
|--------------|-----------|----------------|
| 1-10 pages | ~2GB | 30-60s |
| 10-50 pages | ~4GB | 2-5min |
| 50+ pages | ~8GB+ | 5-15min |

### Optimization Strategies

1. **For Speed**:
   ```python
   config = IngestionConfig(
       detection_dpi=300,          # Lower resolution
       create_visualizations=False # No debug images
   )
   ```

2. **For Accuracy**:
   ```python
   config = IngestionConfig(
       detection_dpi=600,          # Higher resolution
       score_threshold=0.1,        # Catch more regions
       expand_boxes=True,          # Prevent cutoffs
       box_padding=30             # Extra padding
   )
   ```

## Troubleshooting

### Model Download Issues

```bash
# Clear corrupted cache
rm -rf ~/.torch/iopath_cache/

# Reinstall with proper models
make install-detectron2
```

### Text Quality Problems

1. **Missing spaces**: Enable WordNinja processing
2. **Garbled text**: Check if PDF has embedded text (scanned PDFs not supported)
3. **Cut-off text**: Increase `box_padding` parameter
4. **Wrong reading order**: Check column detection threshold

### Layout Detection Issues

1. **Missing regions**: Lower `score_threshold`
2. **Too many boxes**: Increase `nms_threshold` (non-maximum suppression)
3. **Overlapping boxes**: Verify overlap resolver is enabled
4. **Wrong labels**: Ensure correct model (PubLayNet vs PrimaLayout)

## Recent Improvements

### Fixed Issues (July 2025)

1. **Reading Order**: Fixed horizontal overlap detection in hybrid algorithm
2. **K-means Clustering**: Fixed cluster assignment synchronization
3. **Silhouette Score**: Corrected scaling for consistent distance metrics
4. **Configurable Thresholds**: Made same-type merge threshold configurable
5. **Code Cleanup**: Removed duplicate imports

### API Changes

- `no_overlap_pipeline` now accepts `same_type_merge_threshold` parameter
- `_vertical_overlap` renamed to `_horizontal_overlap` (internal)

## Best Practices

1. **Choose the Right Pipeline**:
   - Scientific papers → Scientific pipeline
   - Marketing materials → Marketing pipeline
   - Mixed documents → Process sections separately

2. **Validate Outputs**:
   - Check visualizations for detection quality
   - Verify reading order in `.txt` output
   - Inspect JSON for structure preservation

3. **Handle Errors Gracefully**:
   ```python
   try:
       document = ingest_pdf(pdf_path)
   except Exception as e:
       # Log error and handle appropriately
       logger.error(f"Failed to process PDF: {e}")
   ```

## Future Enhancements

- **OCR Support**: Add text extraction for scanned documents
- **Table Structure**: Extract table cells and relationships
- **Multi-Language**: Support for non-English documents
- **Custom Models**: Train on domain-specific layouts