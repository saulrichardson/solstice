# Marketing Document Processing Module

A specialized module for processing marketing materials using PrimaLayout and optional vision LLM adjustments.

## Features

- **PrimaLayout Detection**: Better suited for marketing documents than PubLayNet
- **Optimized Settings**: Lower thresholds to catch all text content
- **Overlap Resolution**: Automatic merging of overlapping regions
- **Vision LLM Enhancement**: Optional AI-powered layout improvements

## Usage

```python
from injestion.marketing import MarketingPipeline

# Basic usage
pipeline = MarketingPipeline(use_vision_adjustment=False)
document = pipeline.process_pdf("marketing.pdf")

# With vision adjustments (requires OPENAI_API_KEY)
pipeline = MarketingPipeline(use_vision_adjustment=True)
document = pipeline.process_pdf("marketing.pdf")
```

## Components

1. **detector.py**: PrimaLayout-based layout detection
   - Score threshold: 0.1 (catches subtle text)
   - NMS threshold: 0.3 (reduces overlaps)
   - Detects: TextRegion, ImageRegion, TableRegion, etc.

2. **vision_adjuster.py**: OpenAI Vision API integration
   - Merges icon-text pairs
   - Improves semantic grouping
   - Fixes classification errors

3. **pipeline.py**: Complete processing pipeline
   - Layout detection
   - Overlap resolution
   - Text extraction
   - Document formatting

## Results

For the Flublok marketing PDF:
- PubLayNet: ~6 text regions (misses most content)
- PrimaLayout: ~23 text regions (captures all content)
- With overlap resolution: Cleaner, non-overlapping layout

## Configuration

Key parameters in `MarketingPipeline`:
- `use_vision_adjustment`: Enable/disable vision LLM (default: True)
- `score_threshold`: Detection sensitivity (default: 0.1)
- `nms_threshold`: Overlap suppression (default: 0.3)
- `detection_dpi`: Image resolution (default: 400)