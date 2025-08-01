# Ingestion Module

Converts PDFs into structured JSON documents using layout detection.

## Pipelines

### Scientific Pipeline
For clinical and research PDFs.
- Uses PubLayNet model
- Extracts text, figures, tables
- Fixes OCR artifacts

### Marketing Pipeline  
For marketing materials with complex layouts.
- Uses PrimaLayout model
- Handles multi-column layouts
- Aggressive box consolidation

## Output Structure

```
data/scientific_cache/<PDF_NAME>/
├── extracted/
│   ├── content.json      # Structured document
│   ├── document.txt      # Plain text version
│   ├── document.html     # HTML version
│   ├── document.md       # Markdown version
│   └── figures/          # Extracted images (PNG files)
├── pages/                # Full page images (page-000.png, etc.)
├── visualizations/       # Layout detection previews
└── raw_layouts/          # Raw detection data
```

## Usage

```bash
# Process clinical PDFs
python -m src.cli ingest

# Process marketing PDFs  
python -m src.cli ingest-marketing
```