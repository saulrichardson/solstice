# Visualization Module

Debug and quality assurance tools for visual inspection of document processing results.

## Architecture Overview

The visualization module provides comprehensive visual debugging and quality assurance capabilities for the ingestion pipeline. It generates annotated images that help developers and users understand how documents are being processed, identify issues, and validate results.

### Key Responsibilities

- **Layout Visualization**: Render bounding boxes with type-specific colors and labels
- **Reading Order Display**: Show document flow with numbered sequences and arrows
- **Quality Assurance**: Generate summary grids for quick document overview
- **Debug Output**: Create stage-by-stage visualizations for troubleshooting
- **Overlap Analysis**: Highlight conflicting regions for resolution tuning
- **Export Flexibility**: Support multiple output formats (PNG, PDF, SVG)

## Components

### layout_visualizer.py

Main visualization functions for document layouts:

```python
from src.injestion.visualization.layout_visualizer import (
    visualize_page_layout,
    create_summary_grid,
    visualize_document
)

# Visualize single page
fig = visualize_page_layout(
    page_image=img,
    blocks=blocks,
    reading_order=["block1", "block2"],
    save_path="output.png"
)

# Create multi-page summary grid
create_summary_grid(
    doc_id="clinical_study",
    max_pages=4
)

# Visualize entire document
visualize_document(document, output_dir)
```

## Visualization Types

### 1. Page Layout Visualization

Shows detected regions with color-coded boxes:

```python
# Color mapping
COLOR_MAP = {
    'Text': 'blue',      # Regular text blocks
    'Title': 'red',      # Headers and titles
    'List': 'green',     # Bullet points, numbered lists
    'Table': 'purple',   # Tabular data
    'Figure': 'orange',  # Images, charts, diagrams
    'Unknown': 'gray'    # Unclassified regions
}
```

Features:
- Bounding boxes with type labels
- Confidence scores (optional)
- Block IDs for debugging
- Reading order numbers

### 2. Summary Visualization

Grid view of multiple pages:

```python
create_summary_grid(
    doc_id="document",
    max_pages=8,          # Pages per grid
    fig_size=(20, 16)     # Overall figure size
)
```

Useful for:
- Quick document overview
- Quality checking across pages
- Identifying processing issues
- Presentation/reporting

### 3. Reading Order Visualization

Shows document flow with arrows:

```python
visualize_page_layout(
    page_image=img,
    blocks=blocks,
    reading_order=ordered_ids,
    show_arrows=True,
    arrow_color='red'
)
```

Features:
- Numbered sequence
- Flow arrows between blocks
- Column detection visualization
- Skip connections for headers/footers

### 4. Before/After Comparison

Compare raw vs processed layouts:

```python
# Raw detection results
visualize_page_layout(
    page_image=img,
    blocks=raw_blocks,
    title="Before Processing",
    save_path="before.png"
)

# After overlap resolution
visualize_page_layout(
    page_image=img,
    blocks=clean_blocks,
    title="After Processing", 
    save_path="after.png"
)
```

## Usage Examples

### Basic Page Visualization

```python
from PIL import Image
from src.injestion.visualization.layout_visualizer import visualize_page_layout

# Load page image
page_img = Image.open("page-001.png")

# Create visualization
visualize_page_layout(
    page_image=page_img,
    blocks=detected_blocks,
    save_path="page_001_layout.png",
    show_labels=True,
    show_confidence=True
)
```

### Document Processing Pipeline

```python
# Visualize each processing stage
for stage, blocks in processing_stages.items():
    visualize_page_layout(
        page_image=page_img,
        blocks=blocks,
        title=f"Stage: {stage}",
        save_path=f"stage_{stage}.png"
    )
```

### Debugging Overlaps

```python
# Highlight overlapping regions
from src.injestion.processing.box import Box

overlapping = []
for i, box1 in enumerate(blocks):
    for box2 in blocks[i+1:]:
        if box1.intersection_over_union(box2) > 0:
            overlapping.extend([box1, box2])

# Visualize with emphasis
visualize_page_layout(
    page_image=page_img,
    blocks=blocks,
    highlight_blocks=overlapping,
    highlight_color='red',
    save_path="overlaps.png"
)
```

### Quality Reports

```python
# Generate report images
output_dir = Path("quality_report")

# 1. Summary grid
create_summary_grid(
    doc_id=doc_id,
    save_path=output_dir / "summary.png"
)

# 2. Per-page details
for i, (img, blocks) in enumerate(pages_data):
    visualize_page_layout(
        page_image=img,
        blocks=blocks,
        save_path=output_dir / f"page_{i:03d}.png",
        show_stats=True  # Add statistics overlay
    )
```

## Customization Options

### Visual Parameters

```python
visualize_page_layout(
    page_image=img,
    blocks=blocks,
    
    # Box styling
    box_alpha=0.3,          # Transparency
    box_linewidth=2,        # Border width
    
    # Labels
    show_labels=True,       # Type labels
    label_fontsize=12,      # Font size
    label_position='top',   # Label placement
    
    # Colors
    color_map=custom_colors,  # Override defaults
    highlight_color='yellow', # Special blocks
    
    # Figure
    fig_size=(12, 16),      # Image dimensions
    dpi=150                 # Resolution
)
```

### Output Formats

```python
# Save to different formats
save_path = "output.png"    # PNG (default)
save_path = "output.pdf"    # PDF (vector)
save_path = "output.svg"    # SVG (web)

# Or get matplotlib figure
fig = visualize_page_layout(
    page_image=img,
    blocks=blocks,
    save_path=None  # Don't save
)
# Further customize fig...
```

## Integration with Pipeline

### Automatic Visualization

The ingestion pipeline creates visualizations automatically:

```
data/cache/<doc_id>/visualizations/
├── all_pages_summary.png    # Grid overview
├── page_001_layout.png      # Processed layout
├── page_002_layout.png
└── ...

data/cache/<doc_id>/raw_layouts/visualizations/
├── page_001_raw_layout.png  # Raw detection
├── page_002_raw_layout.png
└── ...
```

### Custom Visualization Steps

```python
# In your pipeline
if CREATE_VISUALIZATIONS:
    # After layout detection
    visualize_page_layout(
        page_img, raw_boxes,
        save_path=viz_dir / f"page_{i}_raw.png"
    )
    
    # After processing
    visualize_page_layout(
        page_img, final_blocks,
        save_path=viz_dir / f"page_{i}_final.png"
    )
```

## Performance Considerations

### Memory Usage
- Large images consume significant memory
- Consider downsampling for visualization
- Close figures after saving

### Speed Optimization
```python
# Batch visualization
with plt.ioff():  # Turn off interactive mode
    for page_data in pages:
        visualize_page_layout(...)
```

### File Sizes
- PNG: Best quality/size balance
- JPG: Smaller but lossy
- PDF: Vector format, good for printing
- Adjust DPI based on needs (screen: 72-150, print: 300+)

## Troubleshooting

### Common Issues

1. **Memory errors with large documents**
   ```python
   # Process in batches
   for batch in chunks(pages, size=10):
       create_summary_visualization(batch)
   ```

2. **Slow visualization**
   ```python
   # Reduce quality for speed
   visualize_page_layout(
       page_image=img.resize((800, 1000)),
       dpi=72
   )
   ```

3. **Missing fonts**
   ```python
   # Set matplotlib font
   plt.rcParams['font.family'] = 'DejaVu Sans'
   ```

## Architecture Integration

### With Processing Pipeline
The visualization module is called at key stages:
1. After raw layout detection (raw_layouts/visualizations/)
2. After box consolidation (visualizations/)
3. For final quality reports (all_pages_summary.png)

### With Storage Module
Uses standardized paths:
```python
from ..storage.paths import stage_dir, pages_dir
viz_dir = stage_dir("visualizations", doc_id)
```

### With Document Model
Visualizes structured document objects:
```python
from src.interfaces import Document, Block
visualize_document(document, output_dir)
```

## Design Patterns

### Factory Pattern
Color mapping and style configuration:
```python
COLOR_MAP = {
    'Text': 'blue',
    'Title': 'red',
    'List': 'green',
    'Table': 'purple',
    'Figure': 'orange'
}
```

### Builder Pattern
Incremental figure construction:
```python
fig, ax = plt.subplots()
for box in boxes:
    add_box_to_axes(ax, box)
if show_arrows:
    add_reading_order_arrows(ax, boxes)
```

## Performance Optimization

### Memory Management
```python
# Close figures after saving
plt.close(fig)

# Use context manager
with plt.ioff():
    for page in pages:
        visualize_page_layout(...)
```

### Batch Processing
```python
# Process multiple pages efficiently
def visualize_document_batch(doc_id: str, batch_size: int = 10):
    pages = list(pages_dir(doc_id).glob("*.png"))
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i+batch_size]
        create_batch_visualization(batch)
```

## Future Enhancements

1. **Interactive Visualizations**: Plotly/Bokeh for web-based exploration
2. **3D Layout**: Layer visualization for overlap analysis
3. **Animation**: Processing pipeline as animated GIF/video
4. **Heatmaps**: Confidence score and text density visualization
5. **Diff View**: Side-by-side before/after comparisons
6. **Export Templates**: LaTeX/HTML report generation
7. **Real-time Preview**: Live visualization during processing
8. **Accessibility**: High-contrast modes and colorblind-friendly palettes