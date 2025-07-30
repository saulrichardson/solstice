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
    │   ├── reading_order_hybrid.py  # K-means based column detection
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

### 1. Pipeline Selection

```python
# For research papers, clinical studies, academic documents
from src.injestion.scientific import ingest_pdf
document = ingest_pdf("clinical_study.pdf")

# For marketing materials, brochures, flyers
from src.injestion.marketing.pipeline import MarketingPipeline
pipeline = MarketingPipeline(config)
document = pipeline.process("marketing_brochure.pdf")
```

### 2. Configuration Tuning

```python
# High accuracy configuration
config = IngestionConfig(
    detection_dpi=600,              # Higher resolution for better detection
    score_threshold=0.1,            # Lower threshold to catch more regions
    expand_boxes=True,              # Prevent text cutoffs
    box_padding=30,                 # Extra padding for safety
    create_visualizations=True      # Enable debugging visualizations
)

# Fast processing configuration
config = IngestionConfig(
    detection_dpi=300,              # Lower resolution for speed
    score_threshold=0.3,            # Higher threshold for confident detections
    create_visualizations=False,    # Skip visualization generation
    merge_threshold=0.7             # Aggressive merging for speed
)
```

### 3. Error Handling and Recovery

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def process_pdf_safely(pdf_path: Path) -> Optional[Document]:
    try:
        document = ingest_pdf(pdf_path)
        logger.info(f"Successfully processed {pdf_path.name}")
        return document
    except FileNotFoundError:
        logger.error(f"PDF not found: {pdf_path}")
    except PermissionError:
        logger.error(f"Permission denied accessing: {pdf_path}")
    except Exception as e:
        logger.exception(f"Unexpected error processing {pdf_path}: {e}")
        # Optionally, try with conservative settings
        try:
            config = IngestionConfig(score_threshold=0.5, expand_boxes=False)
            pipeline = PDFIngestionPipeline(config)
            return pipeline.process(pdf_path)
        except:
            return None
```

### 4. Output Validation

```python
def validate_document(document: Document) -> bool:
    """Validate extracted document quality."""
    if not document.blocks:
        logger.warning("No content blocks extracted")
        return False
    
    # Check for reasonable text extraction
    total_text = sum(len(block.content) for block in document.blocks)
    if total_text < 100:
        logger.warning(f"Minimal text extracted: {total_text} characters")
        return False
    
    # Verify reading order
    page_numbers = [block.page_number for block in document.blocks]
    if page_numbers != sorted(page_numbers):
        logger.warning("Blocks not in page order")
    
    return True
```

## Integration Points

### With CLI Module
```python
# src/cli/ingest.py uses the scientific pipeline
from ..injestion.scientific.pipeline import ingest_pdf
```

### With Fact Check Module
```python
# Fact checkers consume Document objects produced by ingestion
from src.interfaces.document import Document
document = ingest_pdf("study.pdf")
# Pass to fact checking orchestrator
```

### With Storage Module
```python
# All pipelines use centralized cache management
from src.injestion.shared.storage.paths import set_cache_root
set_cache_root(Path("/custom/cache"))
```

## Future Enhancements

- **OCR Support**: Add Tesseract integration for scanned documents
- **Table Structure**: Extract table cells, headers, and relationships
- **Multi-Language**: Support for non-English documents with language detection
- **Custom Models**: Fine-tune Detectron2 on domain-specific layouts
- **Streaming Processing**: Handle very large PDFs with streaming architecture
- **Format Support**: Add support for DOCX, HTML, and other formats
- **Semantic Chunking**: Smart document splitting for LLM processing