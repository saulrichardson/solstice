# Marketing Document Processing Module

A specialized ingestion pipeline for processing marketing materials using PrimaLayout with advanced box consolidation.

## Architecture Overview

The marketing pipeline extends the base ingestion architecture with specialized components optimized for complex marketing layouts, multi-column designs, and mixed text/image content. It inherits from `BasePDFPipeline` while providing marketing-specific implementations.

## Key Features

- **PrimaLayout Detection**: Uses a model specifically trained for diverse document layouts (better than PubLayNet for marketing)
- **Smart Box Consolidation**: Advanced algorithms to merge fragmented text regions while preserving visual hierarchy
- **Text Cutoff Prevention**: Intelligent box expansion to capture complete text without creating overlaps
- **Logo Detection**: Heuristic-based identification and reclassification of logo regions
- **Multi-Column Support**: Specialized reading order detection for marketing layouts
- **Configurable Processing**: Preset configurations for different marketing document types

## Usage

### Command Line Interface

```bash
# Basic usage
python run_marketing.py path/to/marketing.pdf

# With custom settings
python run_marketing.py marketing.pdf \
    --merge-threshold 0.1 \
    --box-padding 15.0 \
    --no-visualizations

# Use presets
python run_marketing.py marketing.pdf --preset aggressive
python run_marketing.py marketing.pdf --preset conservative

# View all options
python run_marketing.py --help
```

### Python API

```python
from src.injestion.marketing import MarketingPipeline

# Basic usage
pipeline = MarketingPipeline()
document = pipeline.process_pdf("marketing.pdf")

# Custom settings
pipeline = MarketingPipeline(
    merge_threshold=0.2,          # 20% overlap triggers merge
    expand_boxes=True,            # Fix text cutoffs
    box_padding=10.0              # Expansion amount
)
document = pipeline.process_pdf("marketing.pdf")
```

## Component Architecture

### 1. **MarketingPipeline** (`pipeline.py`)
- **Inheritance**: Extends `BasePDFPipeline` from shared components
- **Responsibilities**:
  - Orchestrates the complete marketing document processing flow
  - Manages PrimaLayout detector initialization
  - Coordinates consolidation, reading order, and text extraction
  - Integrates with shared visualization and storage components
- **Key Methods**:
  - `_create_detector()`: Returns marketing-specific detector
  - `_post_process_boxes()`: Applies consolidation logic
  - `process_pdf()`: Main entry point for processing

### 2. **MarketingLayoutDetector** (`detector.py`)
- **Model**: PrimaLayout (lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config)
- **Label Mapping**:
  ```python
  1: "TextRegion"
  2: "ImageRegion"
  3: "TableRegion"
  4: "MathsRegion"
  5: "SeparatorRegion"
  6: "OtherRegion"
  ```
- **Optimizations**: Lower score threshold (0.15) for marketing materials

### 3. **BoxConsolidator** (`consolidation.py`)
- **Core Operations**:
  - **Logo Detection**: Identifies logos based on position and type
  - **Overlap Resolution**: Removes overlaps between different types
  - **Same-Type Merging**: Consolidates fragmented text regions
  - **Safe Expansion**: Extends boxes without creating new overlaps
- **Algorithms**:
  - IoU-based overlap detection
  - Position-based logo heuristics
  - Iterative expansion with collision detection

### 4. **Marketing Reading Order** (`reading_order.py`)
- **Algorithm**: Feature-based scoring system
- **Factors Considered**:
  - Vertical position (top content first)
  - Horizontal position (left-to-right)
  - Box type priorities (titles before body text)
  - Column detection for multi-column layouts

### 5. **Marketing Pipeline Wrapper** (`marketing_pipeline_wrapper.py`)
- **Purpose**: Adapter for unified interface compatibility
- **Usage**: Allows marketing pipeline to be used interchangeably with scientific pipeline

## Results

For the Flublok marketing PDF:
- Raw detection: ~28 regions with overlaps and fragments
- After consolidation: 19 clean, non-overlapping regions
- Text cutoff issues: Fixed with targeted box extensions
- All marketing claims and details properly captured

## Key Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `score_threshold` | 0.15 | Detection confidence threshold |
| `nms_threshold` | 0.4 | Non-maximum suppression threshold |
| `detection_dpi` | 400 | PDF rasterization DPI |
| `apply_overlap_resolution` | True | Apply box consolidation |
| `expand_boxes` | True | Fix text cutoffs |
| `box_padding` | 10.0 | Pixels to expand boxes |
| `merge_threshold` | 0.2 | IoU threshold (20% overlap) |

## Architecture Benefits

1. **Modular Design**: Each component has a single, well-defined responsibility
2. **Inheritance-Based**: Reuses shared infrastructure while specializing for marketing
3. **Configuration-Driven**: Presets and parameters enable tuning without code changes
4. **Type Safety**: Uses dataclasses and type hints throughout
5. **Clear Separation**: Box operations, detection, and reading order are independent
6. **Extensibility**: Easy to add new consolidation strategies or detection models

## Integration with Core System

### Shared Components Used
- `BasePDFPipeline`: Provides PDF processing framework
- `IngestionConfig`: Configuration management
- `Document`/`Block`: Standard output format
- `TextExtractor`: PyMuPDF-based text extraction
- `LayoutVisualizer`: Debug visualization generation
- Storage paths and cache management

### Output Compatibility
The marketing pipeline produces the same `Document` objects as the scientific pipeline, ensuring seamless integration with downstream fact-checking components.

## Performance Considerations

- **Model Loading**: PrimaLayout model cached after first use
- **Processing Time**: ~30-60s for typical marketing PDFs
- **Memory Usage**: ~2-4GB depending on document complexity
- **Parallel Processing**: Detection runs on GPU if available

## Future Enhancements

1. **ML-Based Logo Detection**: Replace heuristics with trained model
2. **Table Structure Extraction**: Parse marketing comparison tables
3. **Visual Element Analysis**: Extract and analyze charts/infographics
4. **Brand Consistency Checking**: Verify brand guidelines compliance