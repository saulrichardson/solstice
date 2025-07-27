# DPI Handling Guide for Layout Detection

## Overview

This guide explains how to properly handle DPI (dots per inch) when working with PDF layout detection to avoid coordinate misalignment issues.

## The Problem

Layout detection models process PDFs at a specific DPI (typically 200 DPI by default). When visualizing results at a different DPI, the bounding box coordinates must be scaled accordingly, or they will appear misaligned.

### Example of the Issue

```python
# Detection performed at 200 DPI
bbox = {"x1": 800, "y1": 1000, "x2": 1600, "y2": 2000}

# If visualizing at 150 DPI without scaling:
# The box will appear 33% larger than it should!
```

## Best Practices

### 1. Always Use the DPI-Aware Utilities

```python
from src.injestion.utils.visualization import LayoutVisualizer, visualize_with_auto_dpi

# Quick visualization with automatic DPI handling
visualize_with_auto_dpi(
    pdf_path="document.pdf",
    results_path="detection_results.json",
    output_path="visualization.png"
)

# Or use the full visualizer for more control
visualizer = LayoutVisualizer(detection_dpi=200)
visualizer.visualize_layout(
    pdf_path="document.pdf",
    layout_data="detection_results.json",
    visualization_dpi=150,  # Will automatically scale coordinates
    output_path="visualization.png"
)
```

### 2. Track DPI in Your Pipeline

```python
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.utils.visualization import add_dpi_metadata_to_results

# Create pipeline with explicit DPI
pipeline = LayoutDetectionPipeline(detection_dpi=200)
layouts = pipeline.process_pdf("document.pdf")

# Save results with DPI metadata
results = {
    "pages": [...],
    "detection_dpi": 200  # Always include this!
}
```

### 3. Validate DPI Consistency

```python
from src.injestion.utils.visualization import validate_dpi_consistency

# Check if coordinates match expected DPI
is_valid = validate_dpi_consistency(
    pdf_path="document.pdf",
    results=detection_results,
    expected_dpi=200
)

if not is_valid:
    print("Warning: Coordinate/DPI mismatch detected!")
```

### 4. Manual Coordinate Scaling

If you need to manually scale coordinates:

```python
# Scale factor = target_dpi / source_dpi
scale_factor = 150 / 200  # 0.75

# Scale all coordinates
scaled_bbox = {
    "x1": bbox["x1"] * scale_factor,
    "y1": bbox["y1"] * scale_factor,
    "x2": bbox["x2"] * scale_factor,
    "y2": bbox["y2"] * scale_factor,
}
```

## Common DPI Values

- **200 DPI**: Default for pdf2image and most detection models
- **150 DPI**: Common for web visualization (smaller file sizes)
- **300 DPI**: High quality for print or detailed analysis
- **72/96 DPI**: Screen resolution (avoid for detection)

## Debugging Tips

### Check Image Dimensions

```python
from pdf2image import convert_from_path

# Compare dimensions at different DPIs
for dpi in [150, 200, 300]:
    images = convert_from_path("document.pdf", first_page=1, last_page=1, dpi=dpi)
    print(f"{dpi} DPI: {images[0].size}")
```

### Verify Coordinate Bounds

```python
# Maximum coordinates should not exceed image dimensions
image_width, image_height = 1654, 2197  # at 200 DPI

for elem in detection_results:
    bbox = elem["bbox"]
    assert bbox["x2"] <= image_width, f"X coordinate {bbox['x2']} exceeds width {image_width}"
    assert bbox["y2"] <= image_height, f"Y coordinate {bbox['y2']} exceeds height {image_height}"
```

## Migration Guide

### Updating Existing Scripts

1. Replace direct visualization code:

```python
# OLD - May have DPI issues
images = convert_from_path(pdf_path, dpi=150)
# ... draw boxes with raw coordinates ...

# NEW - DPI-aware
from src.injestion.utils.visualization import LayoutVisualizer
visualizer = LayoutVisualizer(detection_dpi=200)
visualizer.visualize_layout(pdf_path, results, visualization_dpi=150)
```

2. Add DPI metadata to saved results:

```python
# When saving detection results
results["detection_dpi"] = 200
```

3. Use the BoundingBox class for coordinate manipulation:

```python
from src.injestion.utils.visualization import BoundingBox

bbox = BoundingBox(x1=100, y1=200, x2=300, y2=400, dpi=200)
scaled_bbox = bbox.scale_to_dpi(150)  # Automatically scales coordinates
```

## Example: Complete DPI-Safe Workflow

```python
from pathlib import Path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.utils.visualization import LayoutVisualizer, add_dpi_metadata_to_results
import json

# 1. Detect layout with explicit DPI
detection_dpi = 200
pipeline = LayoutDetectionPipeline(detection_dpi=detection_dpi)
layouts = pipeline.process_pdf("document.pdf")

# 2. Convert to JSON format with DPI metadata
results = []
for page_idx, page_layout in enumerate(layouts):
    page_data = {
        "page": page_idx + 1,
        "detection_dpi": detection_dpi,
        "elements": [
            {
                "type": str(elem.type),
                "bbox": {
                    "x1": elem.block.x_1,
                    "y1": elem.block.y_1,
                    "x2": elem.block.x_2,
                    "y2": elem.block.y_2,
                },
                "score": float(elem.score)
            }
            for elem in page_layout
        ]
    }
    results.append(page_data)

# 3. Save with metadata
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)

# 4. Visualize at any DPI - coordinates will be scaled automatically
visualizer = LayoutVisualizer(detection_dpi=detection_dpi)
for page_num in range(1, 4):  # First 3 pages
    visualizer.visualize_layout(
        pdf_path="document.pdf",
        layout_data=results,
        page_num=page_num,
        visualization_dpi=150,  # Different from detection DPI
        output_path=f"page_{page_num}_viz.png"
    )
```

## Summary

1. **Always track the DPI** used during detection
2. **Use the provided utilities** for DPI-aware visualization
3. **Scale coordinates** when visualization DPI ≠ detection DPI
4. **Include DPI metadata** in saved results
5. **Validate consistency** to catch mismatches early

By following these practices, you'll avoid the coordinate misalignment issues that occur when DPI values don't match between detection and visualization.