# Ingestion Module

PDF processing system that converts documents into structured JSON using layout detection and text extraction.

## Overview

The ingestion module converts PDFs into structured documents for fact-checking. It uses Detectron2 for layout detection and PyMuPDF for text extraction.

### Core Components

- **Layout Detection**: Detectron2 with pre-trained models (PubLayNet, PrimaLayout)
- **Text Extraction**: PyMuPDF with OCR artifact correction
- **Two Pipelines**: Scientific (clinical documents) and Marketing (visual layouts)
- **Reading Order**: Column detection and vertical ordering
- **Output**: Structured JSON with text blocks and extracted figures

### Available Pipelines

1. **Scientific Pipeline** (`scientific/`): For clinical PDFs and research documents
2. **Marketing Pipeline** (`marketing/`): For marketing materials

## Architecture

### Module Structure

```
injestion/
├── scientific/              # Main pipeline for academic/clinical documents
│   ├── __init__.py         # Exports: ingest_pdf, PDFIngestionPipeline
│   ├── pipeline.py         # High-level orchestration and public API
│   └── standard_pipeline.py # StandardPipeline implementation with PubLayNet
│
├── marketing/              # Specialized pipeline for marketing materials
│   ├── cli.py             # Standalone CLI for marketing processing
│   ├── detector.py        # PrimaLayout-based detection with custom logic
│   ├── pipeline.py        # MarketingPipeline implementation
│   ├── consolidation.py   # Advanced box merging for marketing layouts
│   ├── reading_order.py   # Marketing-specific reading order algorithms
│   └── marketing_pipeline_wrapper.py # Adapter for unified interface
│
└── shared/                 # Common utilities used by both pipelines
    ├── base_pipeline.py   # Abstract base class defining pipeline contract
    ├── config.py          # IngestionConfig with validation and defaults
    ├── processing/        # Core document processing components
    │   ├── layout_detector.py       # Detectron2 wrapper and model management
    │   ├── text_extractor.py        # PyMuPDF-based text extraction
    │   ├── text_processing_service.py # Advanced text cleaning and correction
    │   ├── overlap_resolver.py      # Box overlap detection and resolution
    │   ├── reading_order.py          # Simple reading order detection
    │   └── box.py                   # Core data structures (Box, LabeledBox)
    ├── storage/           # File I/O and cache management
    │   └── paths.py       # Centralized path management and cache structure
    └── visualization/     # Debug and quality assurance tools
        └── layout_visualizer.py     # Generate visual layout representations
```

### Key Classes

- `BasePipeline`: Abstract base class for all pipelines
- `IngestionConfig`: Configuration with validation
- `Box`/`LabeledBox`: Core data structures for layout regions
- `Document`: Output structure with blocks and reading order

## Pipeline Comparison

| Feature | Scientific Pipeline | Marketing Pipeline |
|---------|-------------------|-------------------|
| **Model** | PubLayNet | PrimaLayout |
| **Label IDs** | Start at 0 | Start at 1 |
| **Labels** | Text, Title, List, Table, Figure | TextRegion, ImageRegion, TableRegion, etc. |
| **Reading Order** | Hybrid algorithm | Marketing-specific |
| **Default Threshold** | 0.2 | 0.1 |

## Scientific Pipeline

### Processing Steps

1. **Rasterize PDF** at 400 DPI
2. **Detect layout** using PubLayNet model (labels: Text=0, Title=1, List=2, Table=3, Figure=4)
3. **Resolve overlaps** and expand boxes to prevent text cutoff
4. **Extract text** from boxes using PyMuPDF
5. **Clean text**: Remove PDF artifacts, fix spacing with WordNinja
6. **Save outputs**: content.json, figures/, visualizations/

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

### Processing Steps

1. **Rasterize PDF** at configurable DPI
2. **Detect layout** using PrimaLayout model (labels start at 1: TextRegion, ImageRegion, etc.)
3. **Consolidate boxes** aggressively for marketing layouts
4. **Detect reading order** using marketing-specific algorithm
5. **Extract and clean text** with marketing optimizations
6. **Save outputs** same as scientific pipeline

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

- Scientific: Simple top-to-bottom, left-to-right with column detection
- Marketing: Custom algorithm for complex layouts

## Output Structure

```
data/scientific_cache/<PDF_NAME>/
├── pages/                  # Rasterized page images (PNG)
├── raw_layouts/           # Initial detection results
│   ├── raw_layout_boxes.json
│   └── visualizations/    # Raw layout visualizations
├── extracted/             # Final outputs
│   ├── content.json      # Structured document (Document object)
│   ├── document.txt      # Plain text with reading order
│   ├── document.md       # Markdown with formatting
│   ├── document.html     # HTML with tables
│   └── figures/          # Extracted images (PNG)
├── visualizations/        # Debug visualizations
│   ├── page_*_layout.png # Per-page layout boxes
│   └── all_pages_summary.png
└── agents/                # Fact-checking agent outputs (if run)
    └── claims/            # Per-claim agent results
```
