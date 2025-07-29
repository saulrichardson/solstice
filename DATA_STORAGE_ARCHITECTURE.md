# Data Storage Architecture

## Current Storage Structure

When you run ingestion on a PDF, here's exactly what gets saved and where:

```
data/
├── clinical_files/           # Source PDFs
│   └── FlublokPI.pdf
└── cache/                    # All processed output
    └── FlublokPI/           # One folder per document
        ├── pages/           # Page images (PNG)
        │   ├── page-001.png
        │   ├── page-002.png
        │   └── ...
        ├── raw_layouts/     # Initial detection results
        │   ├── raw_layout_boxes.json
        │   └── visualizations/
        │       └── page_001_raw_layout.png
        ├── merged/          # After overlap resolution
        │   └── merged_boxes.json
        ├── reading_order/   # Reading order
        │   └── reading_order.json
        ├── visualizations/  # Final layout visualizations
        │   ├── page_001_layout.png
        │   └── all_pages_summary.png
        └── extracted/       # FINAL OUTPUT ← This is what agents use
            ├── content.json          # Document model (structured data)
            ├── document.txt          # Plain text version
            ├── document.md           # Markdown version
            ├── document.html         # HTML version
            └── figures/              # Extracted images
                ├── figure_p1_abc123.png
                ├── table_p2_def456.png
                └── ...
```

## What Gets Saved

### 1. Document Model (`content.json`)
```json
{
  "source": "data/clinical_files/FlublokPI.pdf",
  "cache_dir": "data/cache/FlublokPI",
  "blocks": [
    {
      "id": "abc123",
      "page_index": 0,
      "role": "Text",
      "bbox": [100, 200, 500, 300],
      "text": "HIGHLIGHTS OF PRESCRIBING INFORMATION",
      "image_path": null,
      "metadata": {"score": 0.98}
    },
    {
      "id": "def456",
      "page_index": 1,
      "role": "Figure",
      "bbox": [150, 400, 450, 600],
      "text": null,
      "image_path": "figures/figure_p2_def456.png",
      "metadata": {"score": 0.95}
    }
  ],
  "reading_order": [
    ["abc123", "xyz789"],  // Page 0 block IDs in order
    ["def456", "ghi012"]   // Page 1 block IDs in order
  ],
  "metadata": {
    "total_pages": 5,
    "detection_dpi": 400,
    "extraction": {
      "text_blocks": 53,
      "figure_blocks": 8
    }
  }
}
```

### 2. Image Storage
- Figures and tables saved as PNG files
- Path in block: `"figures/figure_p2_def456.png"`
- Actual file: `data/cache/FlublokPI/extracted/figures/figure_p2_def456.png`

### 3. Multiple Output Formats
- **document.txt**: Plain text for simple processing
- **document.md**: Markdown with image references
- **document.html**: HTML with embedded images

## How Saving Works in Pipeline

```python
# src/injestion/pipeline.py

def ingest_pdf(pdf_path: str, text_extractor: str) -> Document:
    # ... processing ...
    
    # Create Document object
    document = Document(
        source_pdf=str(pdf_path),
        blocks=blocks,
        metadata={...},
        reading_order=reading_order_by_page
    )
    
    # Extract content (including saving figures)
    document = extract_document_content(document, pdf_path, dpi, text_extractor)
    
    # Save the document model
    extracted_dir = stage_dir("extracted", pdf_path)  # Creates cache/DocName/extracted/
    document.save(extracted_dir / "content.json")
    
    # Generate other formats
    generate_readable_document(document, extracted_dir / "document.md")
    generate_text_only_document(document, extracted_dir / "document.txt")
    generate_html_document(document, extracted_dir / "document.html")
```

## With New Interface Design

### What Changes
1. **Document model moves** from `injestion.models.document` to `interfaces.document`
2. **Same storage structure** - No changes to file locations
3. **cache_dir field** added to Document for explicit path tracking

### Loading with New Interface
```python
from src.interfaces import Document, StandardDocumentReader

# Load document (same file, new import)
doc = Document.load("data/cache/FlublokPI/extracted/content.json")

# Reader knows where to find images
reader = StandardDocumentReader(doc)
# Automatically resolves: figures/figure_p2_def456.png
# To: data/cache/FlublokPI/extracted/figures/figure_p2_def456.png

# When vision agent needs image
item = reader.get_vision_content()[5]  # Some figure
image = item.load_image()  # Loads from disk path
```

## Storage Path Resolution

```python
class Document:
    source: str  # "data/clinical_files/FlublokPI.pdf"
    cache_dir: str  # "data/cache/FlublokPI" (optional, can be inferred)
    
    def get_cache_path(self) -> Path:
        if self.cache_dir:
            return Path(self.cache_dir)
        # Infer from source
        source_path = Path(self.source)
        doc_name = source_path.stem  # "FlublokPI"
        return Path("data/cache") / doc_name

class StandardDocumentReader:
    def __init__(self, document: Document):
        self.document = document
        # Base path for images
        self.base_path = document.get_cache_path() / "extracted"
    
    def resolve_image_path(self, relative_path: str) -> Path:
        # "figures/figure_p2_def456.png"
        # → "data/cache/FlublokPI/extracted/figures/figure_p2_def456.png"
        return self.base_path / relative_path
```

## Benefits of This Approach

1. **Self-Describing**: Document knows where its resources are
2. **Portable**: Can move cache folders, just update cache_dir
3. **Efficient**: No embedded data, just paths
4. **Flexible**: Easy to add cloud storage later

## Future: Cloud Storage

```python
# Future enhancement
class Block:
    image_path: str  # Local: "figures/fig1.png"
    image_url: str   # Cloud: "s3://bucket/doc123/figures/fig1.png"
    
# Reader would check both
if block.image_url and self.use_cloud:
    return load_from_s3(block.image_url)
else:
    return load_from_disk(self.base_path / block.image_path)
```

## Summary

- **Nothing changes** in terms of where files are saved
- **Same directory structure** under `data/cache/`
- **Document model** just moves to interfaces package
- **Paths stay relative** for portability
- **Reader handles** path resolution automatically