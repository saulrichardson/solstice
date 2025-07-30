# Data Directory Structure

Comprehensive guide to Solstice's data organization and storage patterns.

## Overview

The `data/` directory contains all input documents, processed outputs, and intermediate results from the Solstice pipeline. It follows a hierarchical structure that mirrors the processing stages, making it easy to locate specific data types.

## Directory Structure

```
data/
├── cache/                    # Main processing output directory
├── claims/                   # Claim definition files
├── clinical_files/          # Input PDFs (clinical/scientific)
├── marketing_slide/         # Input PDFs (marketing materials)
├── marketing_cache/         # Marketing pipeline outputs
├── studies/                 # Fact-checking study results
└── test_cache/             # Test outputs (gitignored)
```

## Detailed Structure

### 1. Input Documents

#### `clinical_files/`
Original PDF documents for scientific/clinical processing:
```
clinical_files/
├── Arunachalam et al. (2021).pdf
├── CDC Influenza vaccines.pdf
├── FlublokPI.pdf
├── Grohskopf et al. (2023).pdf
├── Hsiao et al. (2023).pdf
├── Liu et al. (2024).pdf
├── Treanor et al. (2011).pdf
└── Zimmerman et al. (2023).pdf
```

#### `marketing_slide/`
Marketing materials for specialized processing:
```
marketing_slide/
└── FlublokOnePage.pdf
```

### 2. Claims Files

#### `claims/`
JSON files containing claims to be fact-checked:
```
claims/
└── Flublok_Claims.json
```

**Format:**
```json
{
  "claims": [
    {
      "id": "claim_000",
      "text": "Flublok Quadrivalent is approved for use in adults 18 years of age and older"
    }
  ]
}
```

### 3. Processed Document Cache

#### `cache/<document_name>/`
Each processed document gets its own directory with standardized structure:

```
cache/FlublokPI/
├── pages/                    # Rasterized page images
│   ├── page-000.png
│   ├── page-001.png
│   └── ...
├── raw_layouts/             # Initial ML detection results
│   ├── raw_layout_boxes.json
│   └── visualizations/      # Per-page detection visualizations
│       └── page_XXX_raw_layout.png
├── merged/                  # Post-consolidation layouts
│   └── merged_boxes.json
├── reading_order/           # Document flow analysis
│   └── reading_order.json
├── extracted/               # Final processed content
│   ├── content.json        # Structured document (primary output)
│   ├── document.txt        # Plain text version
│   ├── document.md         # Markdown version
│   ├── document.html       # HTML version
│   └── figures/            # Extracted images
│       ├── figure_p1_abc123.png
│       ├── table_p2_def456.png
│       └── ...
├── visualizations/          # Final layout visualizations
│   ├── all_pages_summary.png
│   └── page_XXX_layout.png
└── agents/                  # Fact-checking outputs
    └── claims/              # Per-claim analysis results
        └── claim_XXX/       # Individual claim results
```

### 4. Fact-Checking Results

#### `cache/<document_name>/agents/`
Hierarchical storage of fact-checking agent outputs:

```
agents/
├── claims/
│   └── claim_000/           # Per-claim results
│       ├── evidence_extractor/
│       │   └── output.json
│       ├── evidence_verifier_v2/
│       │   └── output.json
│       ├── completeness_checker/
│       │   └── output.json
│       ├── image_evidence_analyzer/
│       │   └── output.json
│       └── evidence_presenter/
│           └── output.json
├── evidence_extractor/      # Legacy: document-level results
├── evidence_verifier_v2/
├── completeness_checker/
├── image_evidence_analyzer/
└── evidence_presenter/
```

### 5. Study Results

#### `studies/`
Comprehensive fact-checking study outputs:
```
studies/
├── study_results_20250729_174932.json
└── study_results_20250729_180914.json
```

**Contains:**
- All claim-document pairs analyzed
- Supporting/contradicting evidence
- Image analysis results
- Completeness assessments
- Processing metadata

## Key Files Explained

### Document Files

#### `content.json`
Primary structured representation of processed document:
```json
{
  "source_pdf": "FlublokPI.pdf",
  "cache_dir": "data/cache",
  "blocks": [
    {
      "id": "block_001",
      "page_index": 0,
      "role": "Title",
      "bbox": [100, 200, 500, 250],
      "text": "FLUBLOK QUADRIVALENT"
    }
  ],
  "reading_order": [["block_001", "block_002", ...]],
  "metadata": {...}
}
```

#### `raw_layout_boxes.json`
ML model detection output before processing:
```json
{
  "pages": [
    {
      "page_number": 1,
      "boxes": [
        {
          "x1": 100, "y1": 200, "x2": 500, "y2": 300,
          "label": "Text",
          "score": 0.95
        }
      ]
    }
  ]
}
```

### Agent Output Files

#### Evidence Extractor Output
```json
{
  "claim": "Flublok is FDA approved",
  "evidence": [
    {
      "text": "FDA approved Flublok Quadrivalent...",
      "location": "Page 1, Section 1",
      "relevance": "high"
    }
  ]
}
```

#### Image Analyzer Output
```json
{
  "analyzed_images": [
    {
      "filename": "table_p1_abc123.png",
      "supports_claim": true,
      "explanation": "Table shows FDA approval dates..."
    }
  ]
}
```

## Finding Specific Data

### To Find Processed Text
```bash
# All extracted text for a document
cat data/cache/FlublokPI/extracted/document.txt

# Structured content with metadata
cat data/cache/FlublokPI/extracted/content.json
```

### To Find Images/Tables
```bash
# All extracted figures
ls data/cache/FlublokPI/extracted/figures/

# Visualizations showing what was detected
ls data/cache/FlublokPI/visualizations/
```

### To Find Fact-Checking Results
```bash
# Specific claim analysis
cat data/cache/FlublokPI/agents/claims/claim_000/evidence_presenter/output.json

# All study results
cat data/studies/study_results_*.json
```

### To Find Processing Metadata
```bash
# Layout detection results
cat data/cache/FlublokPI/raw_layouts/raw_layout_boxes.json

# Reading order
cat data/cache/FlublokPI/reading_order/reading_order.json
```

## Common Tasks

### 1. Check if Document is Processed
```bash
# Look for extracted content
ls data/cache/YourDocument/extracted/content.json
```

### 2. View Document Processing Quality
```bash
# Open summary visualization
open data/cache/YourDocument/visualizations/all_pages_summary.png
```

### 3. Find Evidence for Specific Claim
```bash
# Check claim results
cat data/cache/*/agents/claims/claim_XXX/evidence_presenter/output.json
```

### 4. Debug Processing Issues
```bash
# Check raw detection
open data/cache/YourDocument/raw_layouts/visualizations/page_001_raw_layout.png

# Compare with final
open data/cache/YourDocument/visualizations/page_001_layout.png
```

## Storage Patterns

### Naming Conventions

1. **Document IDs**: Derived from PDF filename
   - Special characters replaced with underscore
   - Example: `Liu et al. (2024).pdf` → `Liu_et_al.__2024_`

2. **Figure Naming**: `{type}_p{page}_{hash}.png`
   - `figure_p1_abc123.png` - Figure from page 1
   - `table_p2_def456.png` - Table from page 2

3. **Timestamps**: Study results use `YYYYMMDD_HHMMSS`

### File Formats

- **JSON**: Configuration, metadata, structured data
- **PNG**: Page renders, figures, visualizations
- **TXT**: Plain text exports
- **MD**: Markdown formatted text
- **HTML**: Rich text with tables

## Disk Usage Considerations

### Typical Sizes

- **Page Images**: ~500KB-2MB per page (400 DPI)
- **Extracted Figures**: ~50KB-500KB each
- **JSON Files**: ~10KB-1MB depending on document size
- **Full Document Cache**: ~50MB-200MB

### Cleanup Strategies

```bash
# Remove intermediate files, keep final outputs
rm -rf data/cache/*/raw_layouts/
rm -rf data/cache/*/merged/
rm -rf data/cache/*/pages/

# Remove visualizations
rm -rf data/cache/*/visualizations/

# Remove all cache for a document
rm -rf data/cache/DocumentName/

# Clear all test data
rm -rf data/test_cache/
```

## Best Practices

1. **Regular Cleanup**: Remove intermediate files after processing
2. **Backup Important Results**: Keep `studies/` and `extracted/` directories
3. **Version Control**: Don't commit large binary files (use .gitignore)
4. **Monitoring**: Check disk usage regularly with `du -sh data/cache/*`
5. **Organization**: Keep input PDFs in appropriate directories

## Troubleshooting

### Missing Files
- Check document was processed: `ls data/cache/`
- Verify pipeline completed: Look for `extracted/content.json`

### Large Cache Size
- Remove page images after processing
- Clear visualization files
- Use cleanup scripts

### Finding Old Results
- Check `studies/` directory for timestamped results
- Look in `agents/` subdirectories for intermediate outputs