# Storage Module

Standardized file organization and path management for the ingestion pipeline.

## Architecture Overview

The storage module serves as the data persistence layer for the ingestion system, providing a consistent interface for managing all files generated during PDF processing. It implements a hierarchical storage structure that mirrors the processing pipeline stages.

### Key Responsibilities

- **Path Management**: Centralized control over file locations and naming
- **Safe Naming**: Filesystem-compatible document ID generation
- **Stage Organization**: Structured directories for each processing stage
- **JSON Persistence**: Standardized serialization for metadata
- **Runtime Configuration**: Dynamic path customization for different environments
- **Cache Management**: Efficient storage and retrieval of processed documents

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

## Implementation Details

### Document ID Generation
```python
def doc_id(pdf_filename: str | os.PathLike) -> str:
    """Generate filesystem-safe document ID.
    
    Algorithm:
    1. Extract basename from path
    2. Remove .pdf extension (case-insensitive)
    3. Replace special chars with underscore
    4. Validate result is non-empty
    5. Fallback to SHA-256 hash (first 8 chars) if invalid
    
    Examples:
        "report.pdf" → "report"
        "Study (2024).pdf" → "Study__2024_"
        "../../etc/passwd" → "8d969eef" (hash)
        "..pdf" → "b6c340a2" (hash - invalid name)
    """
```

### Cache Root Management
```python
# Global state for cache directory
_CACHE_DIR = Path(settings.filesystem_cache_dir)

def set_cache_root(cache_root: os.PathLike | str) -> None:
    """Override the cache directory at runtime.
    
    This allows:
    - CLI --output-dir flag support
    - Testing with temporary directories
    - Multi-tenant deployments
    - Custom storage backends
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

## Architecture Principles

1. **Predictable Structure**: Consistent directory layout across all documents
2. **Safe Naming**: Robust handling of any input filename, including edge cases
3. **Lazy Creation**: Directories created on-demand to avoid empty structures
4. **JSON Standard**: All metadata serialized as pretty-printed JSON for debugging
5. **Configurable Root**: Runtime path override without code changes
6. **Stage Isolation**: Each processing stage has its own directory
7. **Immutable Outputs**: Write-once semantics for reproducibility

## Integration with Processing Pipeline

### Stage Correspondence
```
Processing Stage          Storage Directory
----------------          -----------------
PDF Rasterization    →    pages/
Layout Detection     →    raw_layouts/
Box Consolidation    →    merged/
Reading Order        →    reading_order/
Text Extraction      →    extracted/
Visualization        →    visualizations/
```

### Data Flow
1. **Input**: PDF file with arbitrary name
2. **Doc ID**: Generated for filesystem safety
3. **Staging**: Each processor writes to its stage directory
4. **Output**: Final document in extracted/content.json
5. **Cleanup**: Optional removal of intermediate stages

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

## Performance Considerations

### Filesystem Optimization
- Use SSD storage for cache directory
- Consider separate volumes for different stages
- Enable filesystem compression if available
- Monitor inode usage for large document sets

### Caching Strategy
- Intermediate results enable incremental processing
- Stage directories can be selectively cleared
- JSON files are human-readable but larger than binary
- Consider compression for long-term storage

## Security Considerations

1. **Path Traversal**: Document IDs sanitized to prevent directory escape
2. **Name Collisions**: Hash fallback ensures unique IDs
3. **Permissions**: Cache directory should be writable only by service
4. **Sensitive Data**: No encryption by default - add if needed

## Future Enhancements

1. **Cloud Storage**: S3/GCS backend implementation
2. **Compression**: Automatic gzip for JSON and images
3. **Versioning**: Support multiple versions of same document
4. **Metadata DB**: SQLite index for fast queries and search
5. **Garbage Collection**: TTL-based cleanup policies
6. **Streaming**: Direct-to-storage without intermediate files
7. **Deduplication**: Content-based addressing for efficiency