# Scientific Document Processing Module

A specialized ingestion pipeline optimized for academic papers, clinical studies, and research documents using PubLayNet.

## Architecture Overview

The scientific pipeline is the primary document processing system in Solstice, designed specifically for structured academic and clinical documents. It extends `BasePDFPipeline` with optimizations for research papers, clinical trials, and scientific publications.

## Key Features

- **PubLayNet Detection**: Uses a model trained on 360k+ academic documents for accurate layout detection
- **Clinical Document Optimization**: Default settings tuned for medical and pharmaceutical documents
- **Functional Consolidation**: Lightweight box processing without complex merging
- **Medical Term Preservation**: Intelligent text processing that maintains technical terminology
- **High-Resolution Processing**: 400 DPI default for accurate text extraction
- **Structured Output**: Produces clean, fact-checkable document representations

## Component Architecture

### 1. **Pipeline Entry Point** (`pipeline.py`)
- **Function**: `ingest_pdf()` - Simple API for PDF processing
- **Purpose**: High-level orchestration and backward compatibility
- **Configuration**: Uses optimized defaults for clinical documents
- **Returns**: Standard `Document` object for downstream processing

### 2. **StandardPipeline** (`standard_pipeline.py`)
- **Inheritance**: Extends `BasePDFPipeline` from shared components
- **Key Responsibilities**:
  - PDF to image conversion at configured DPI
  - Layout detection using PubLayNet model
  - Box consolidation and overlap resolution
  - Reading order determination
  - Text extraction and processing
  - Output generation and caching
- **Special Features**:
  - Always saves raw layouts for debugging
  - Applies functional consolidation (no complex merging)
  - Uses simple reading order for single-column documents

### 3. **PubLayNet Model Integration**
- **Model**: lp://PubLayNet/mask_rcnn_X_101_32x8d_FPN_3x/config
- **Label Mapping**:
  ```python
  0: "Text"      # Body text paragraphs
  1: "Title"     # Section headers and titles
  2: "List"      # Bulleted or numbered lists
  3: "Table"     # Tabular data
  4: "Figure"    # Images, charts, diagrams
  ```
- **Optimizations**: 
  - Lower score threshold (0.2) for comprehensive detection
  - Box expansion to prevent text cutoffs
  - Overlap resolution for clean output

## Usage Patterns

### Simple API Usage
```python
from src.injestion.scientific import ingest_pdf

# Process a clinical study PDF
document = ingest_pdf("clinical_trial_results.pdf")

# Access structured content
for block in document.blocks:
    print(f"Page {block.page_number}: {block.label} - {block.content[:100]}...")
```

### Advanced Configuration
```python
from src.injestion.scientific import PDFIngestionPipeline
from src.injestion.shared.config import IngestionConfig

# Custom configuration for specific needs
config = IngestionConfig(
    detection_dpi=600,              # Higher quality for complex layouts
    score_threshold=0.1,            # Catch more subtle regions
    expand_boxes=True,              # Prevent text cutoffs
    box_padding=25,                 # Extra padding for safety
    save_intermediate_states=True   # Enable debugging outputs
)

pipeline = PDFIngestionPipeline(config=config)
document = pipeline.process_pdf("complex_research_paper.pdf")
```

### CLI Integration
```bash
# Standard clinical document processing
python -m src.cli ingest

# Process specific directory
python -m src.cli ingest --output-dir /custom/cache
```

## Processing Flow

```
Clinical/Academic PDF
        │
        ├─► Page Rasterization (400 DPI default)
        │        │
        │        └─► PubLayNet Detection (Detectron2)
        │                 │
        │                 ├─► Raw Layout Boxes with confidence scores
        │                 │
        │                 └─► Functional Consolidation
        │                          │
        │                          ├─► Overlap Resolution
        │                          ├─► Box Expansion (prevent cutoffs)
        │                          └─► Type-based processing
        │
        └─► Text Extraction (PyMuPDF)
                 │
                 ├─► Medical-Aware Text Processing
                 │    ├─► Preserve drug names (e.g., "Flublok®")
                 │    ├─► Fix spacing issues ("patientdata" → "patient data")
                 │    └─► Maintain technical formatting
                 │
                 └─► Document Assembly
                          │
                          └─► Structured Output (JSON/MD/HTML)
```

## Configuration Defaults

The scientific pipeline uses these optimized defaults:

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| `detection_dpi` | 400 | Balance between quality and processing speed |
| `score_threshold` | 0.2 | Conservative threshold for academic documents |
| `expand_boxes` | True | Prevent text cutoffs common in PDFs |
| `box_padding` | 10 | Sufficient padding without overlap issues |
| `merge_threshold` | 0.5 | Moderate merging for clean output |
| `text_extractor` | "pymupdf" | Best extraction quality |
| `preserve_medical_terms` | True | Critical for clinical documents |

## Output Structure

The pipeline generates comprehensive outputs in the cache directory:

```
data/scientific_cache/<PDF_NAME>/
├── pages/                    # Rasterized pages at detection DPI
├── raw_layouts/             # Unprocessed detection results
│   └── raw_layout_boxes.json
├── merged/                  # Post-consolidation layouts
│   └── merged_boxes.json    
├── reading_order/           # Document flow analysis
│   └── reading_order.json
├── extracted/               # Final outputs
│   ├── content.json        # Structured Document object
│   ├── document.txt        # Plain text with reading order
│   ├── document.md         # Markdown with formatting
│   ├── document.html       # HTML with preserved tables
│   └── figures/            # Extracted images (PNG)
└── visualizations/          # Debug overlays
    └── page_*_layout.png   # Annotated layout visualizations
```

## Integration with Fact Checking

The scientific pipeline is specifically designed to support fact-checking workflows:

1. **Structured Output**: Clean `Document` objects with typed blocks
2. **Preserved Context**: Reading order maintains logical flow
3. **Medical Accuracy**: Technical terms remain intact
4. **Table Preservation**: Clinical data tables extracted cleanly
5. **Figure References**: Images linked to surrounding text

## Performance Characteristics

- **Processing Speed**: ~3-5 seconds per page (400 DPI)
- **Memory Usage**: ~1-2GB for typical documents
- **Model Loading**: One-time ~5 second initialization
- **GPU Acceleration**: Automatic if CUDA available

## Best Practices

1. **Document Preparation**:
   - Ensure PDFs have embedded text (not scanned)
   - Higher quality PDFs yield better results
   - Avoid heavily compressed PDFs

2. **Configuration Tuning**:
   ```python
   # For simple documents (faster processing)
   config = IngestionConfig(detection_dpi=300, create_visualizations=False)
   
   # For complex layouts (higher accuracy)
   config = IngestionConfig(detection_dpi=600, score_threshold=0.1)
   ```

3. **Error Handling**:
   ```python
   try:
       document = ingest_pdf(pdf_path)
   except FileNotFoundError:
       logger.error(f"PDF not found: {pdf_path}")
   except Exception as e:
       logger.error(f"Processing failed: {e}")
       # Optionally retry with conservative settings
   ```

## Comparison with Marketing Pipeline

| Feature | Scientific Pipeline | Marketing Pipeline |
|---------|-------------------|-------------------|
| **Target Documents** | Research papers, clinical studies | Brochures, flyers, ads |
| **Model** | PubLayNet | PrimaLayout |
| **Consolidation** | Functional (no merging) | Advanced (aggressive merging) |
| **Reading Order** | Simple algorithm | Feature-based scoring |
| **Default DPI** | 400 | 400 |
| **Text Processing** | Medical term preservation | Standard processing |

## Future Enhancements

1. **Table Structure Extraction**: Parse clinical trial data tables
2. **Citation Linking**: Connect references to bibliography
3. **Formula Recognition**: Extract mathematical equations
4. **Multi-Language Support**: Process non-English research
5. **Incremental Processing**: Handle document updates efficiently