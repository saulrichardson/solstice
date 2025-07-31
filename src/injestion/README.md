# Ingestion Module

High-performance PDF processing system with ML-powered layout detection and intelligent text extraction.

## Overview

The ingestion module is the document processing engine of Solstice, converting PDFs into structured, searchable documents for fact-checking and analysis. It employs state-of-the-art computer vision models (Detectron2) and advanced text processing algorithms to handle diverse document types.

### Core Capabilities

- **ML-Based Layout Detection**: Uses pre-trained Detectron2 models for accurate region identification
- **Intelligent Text Extraction**: Context-aware text processing with medical term preservation
- **Multi-Pipeline Architecture**: Specialized pipelines for different document types
- **Reading Order Detection**: Advanced algorithms for multi-column and complex layouts
- **Quality Assurance**: Built-in visualization and validation tools

### Available Pipelines

1. **Scientific Pipeline** (`scientific/`): Optimized for academic papers, clinical studies, and research documents
2. **Marketing Pipeline** (`marketing/`): Specialized for marketing materials with complex visual layouts

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

### Design Patterns

1. **Abstract Base Pipeline**: All pipelines inherit from `BasePipeline` for consistency
2. **Strategy Pattern**: Different text extractors and processors can be swapped
3. **Builder Pattern**: Pipelines assemble documents through sequential processing steps
4. **Singleton Models**: Detectron2 models are loaded once and reused
5. **Immutable Configuration**: `IngestionConfig` validates settings at creation

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

The reading order detection uses a simple algorithm (`reading_order.py`):
   - Top-to-bottom, left-to-right ordering
   - Suitable for most document layouts
   - Handles basic column detection

## Output Structure

```
data/scientific_cache/<PDF_NAME>/
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
