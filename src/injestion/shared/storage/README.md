# Storage Module

Standardized file organization and path management for the ingestion pipeline.

## Overview

The storage module provides a consistent interface for managing all files generated during PDF processing. It ensures:
- **Organized Structure**: Predictable file locations
- **Safe Naming**: Filesystem-compatible document IDs
- **Easy Access**: Helper functions for common operations
- **Configurable Paths**: Runtime path customization

## Directory Structure

```
data/
├── cache/                          # All processed outputs
│   └── <document_id>/             # Per-document folder
│       ├── pages/                 # Rasterized pages
│       │   ├── page-000.png
│       │   ├── page-001.png
│       │   └── ...
│       ├── raw_layouts/           # Initial detection
│       │   ├── raw_layout_boxes.json
│       │   └── visualizations/
│       │       └── page_XXX_raw_layout.png
│       ├── merged/                # Post-processing
│       │   └── merged_boxes.json
│       ├── reading_order/         # Document flow
│       │   └── reading_order.json
│       ├── extracted/             # Final content
│       │   ├── content.json       # Structured document
│       │   ├── document.txt       # Plain text
│       │   ├── document.md        # Markdown
│       │   ├── document.html      # HTML
│       │   └── figures/           # Extracted images
│       │       ├── figure_p1_xxx.png
│       │       └── table_p2_yyy.png
│       └── visualizations/        # Debug images
│           ├── all_pages_summary.png
│           └── page_XXX_layout.png
└── raw/                           # Original PDFs (optional)
```

## Core Functions

### paths.py

Primary interface for path management:

```python
from src.injestion.storage.paths import (
    doc_id, pages_dir, stage_dir, 
    save_json, load_json, set_cache_root
)

# Get safe document ID from filename
doc_id = doc_id("Clinical Study (2024).pdf")
# Returns: "Clinical_Study__2024_"

# Get standard directories
pages = pages_dir(doc_id)           # data/cache/<doc_id>/pages/
layouts = stage_dir("raw_layouts", doc_id)  # data/cache/<doc_id>/raw_layouts/

# Save/load JSON data
save_json(data, stage_dir("extracted", doc_id) / "content.json")
content = load_json(stage_dir("extracted", doc_id) / "content.json")

# Change output location
set_cache_root("/custom/output/path")
```

## Key Functions

### Document ID Generation
```python
def doc_id(pdf_filename: str | os.PathLike) -> str:
    """Generate filesystem-safe document ID.
    
    Rules:
    1. Remove .pdf extension
    2. Replace special chars with underscore
    3. Fallback to hash if empty/invalid
    
    Examples:
        "report.pdf" → "report"
        "Study (2024).pdf" → "Study__2024_"
        "../../etc/passwd" → "8d969eef" (hash)
    """
```

### Directory Access
```python
# Standard stage directories
pages_dir(doc_id)                    # Rasterized pages
stage_dir("raw_layouts", doc_id)     # Layout detection results
stage_dir("merged", doc_id)          # Overlap resolution
stage_dir("reading_order", doc_id)   # Reading flow
stage_dir("extracted", doc_id)       # Final output

# Ensure directory exists
path = stage_dir("custom", doc_id)
path.mkdir(parents=True, exist_ok=True)
```

### JSON Utilities
```python
# Save with pretty printing
save_json({"key": "value"}, path)

# Load with error handling
data = load_json(path)  # Returns None if not found

# Check existence
if (path := stage_dir("extracted", doc_id) / "content.json").exists():
    data = load_json(path)
```

## Usage Patterns

### Processing Pipeline
```python
# 1. Setup paths for new document
pdf_path = Path("input.pdf")
doc_id = doc_id(pdf_path.name)

# 2. Save rasterized pages
for i, page_img in enumerate(pages):
    page_path = pages_dir(doc_id) / f"page-{i:03d}.png"
    page_img.save(page_path)

# 3. Save intermediate results
save_json(layout_boxes, stage_dir("raw_layouts", doc_id) / "raw_layout_boxes.json")
save_json(merged_boxes, stage_dir("merged", doc_id) / "merged_boxes.json")

# 4. Save final output
output_dir = stage_dir("extracted", doc_id)
save_json(document.dict(), output_dir / "content.json")
```

### Reading Results
```python
# Load processed document
doc_id = doc_id("clinical_study.pdf")
content = load_json(stage_dir("extracted", doc_id) / "content.json")

# Access figures
figures_dir = stage_dir("extracted", doc_id) / "figures"
for fig_path in figures_dir.glob("*.png"):
    # Process figure
    pass
```

### Custom Output Location
```python
# CLI with custom output
# python -m src.cli ingest --output-dir /my/custom/path

# Or programmatically
from src.injestion.storage.paths import set_cache_root
set_cache_root("/my/custom/path")

# All subsequent operations use new root
pages = pages_dir(doc_id)  # /my/custom/path/<doc_id>/pages/
```

## Design Principles

1. **Predictable Structure**: Same layout for all documents
2. **Safe Naming**: Handle any input filename safely
3. **Lazy Creation**: Directories created only when needed
4. **JSON Standard**: All metadata in JSON format
5. **Configurable Root**: Easy to redirect output

## Best Practices

### Path Construction
```python
# Good: Use provided functions
path = stage_dir("extracted", doc_id) / "content.json"

# Bad: Manual path construction
path = Path("data/cache") / doc_id / "extracted/content.json"
```

### Error Handling
```python
# Check before loading
if (content_path := stage_dir("extracted", doc_id) / "content.json").exists():
    content = load_json(content_path)
else:
    print(f"No content found for {doc_id}")
```

### Cleanup
```python
import shutil

# Remove all data for a document
doc_cache = Path(settings.filesystem_cache_dir) / doc_id
if doc_cache.exists():
    shutil.rmtree(doc_cache)
```

## Configuration

### Environment Variables
```bash
# Set cache directory
export FILESYSTEM_CACHE_DIR=/path/to/cache

# Or in .env file
FILESYSTEM_CACHE_DIR=data/cache
```

### Runtime Override
```python
# For testing or custom workflows
set_cache_root("/tmp/test_cache")

# Reset to default
from src.core.config import settings
set_cache_root(settings.filesystem_cache_dir)
```

## Future Enhancements

- **S3 Backend**: Cloud storage support
- **Compression**: Automatic gzip for JSON files
- **Versioning**: Multiple versions of same document
- **Metadata DB**: SQLite index for fast queries
- **Garbage Collection**: Auto-cleanup of old files