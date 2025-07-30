# Document Viewer Module

The viewer module provides tools for creating unified, easy-to-view presentations of multiple extracted documents from the Solstice ingestion pipeline.

## Features

- **Multi-Document Aggregation**: Collect and organize all extracted documents
- **Multiple Output Formats**: Generate static HTML sites, single-page HTML, or JSON
- **Full-Text Search**: Search across all documents with preview snippets
- **Image Support**: Include extracted figures and tables with proper captions
- **Statistics**: View comprehensive statistics about document collection
- **Print-Friendly**: Optimized CSS for clean printed output

## Usage

### Command Line Interface

```bash
# Generate a multi-page HTML site (default)
python -m src.viewer.cli

# Generate a single HTML file with all documents
python -m src.viewer.cli --format single-html --output unified.html

# Search across all documents
python -m src.viewer.cli --search "vaccine efficacy"

# Generate without images (faster, smaller)
python -m src.viewer.cli --no-images

# Open result in browser automatically
python -m src.viewer.cli --open
```

### Programmatic Usage

```python
from pathlib import Path
from src.viewer import DocumentAggregator, UnifiedHTMLGenerator

# Initialize aggregator
aggregator = DocumentAggregator(Path("data/cache"))

# Search functionality
results = aggregator.search_content("clinical trial")
for result in results[:10]:
    print(f"{result['document']}: {result['match_preview']}")

# Generate unified view
generator = UnifiedHTMLGenerator(aggregator)

# Option 1: Multi-page site
index_path = generator.generate_unified_site(Path("output/site"))

# Option 2: Single HTML file
single_path = generator.generate_single_page_html(Path("output/all.html"))

# Option 3: Export as JSON for custom processing
json_path = aggregator.export_combined_json(Path("output/combined.json"))
```

## Output Formats

### 1. Multi-Page HTML Site

Creates a complete static website with:
- `index.html` - Main page with document list and statistics
- `documents/` - Individual HTML pages for each document
- `assets/figures/` - All extracted images
- `style.css` - Responsive styling
- `search.js` - Client-side search functionality
- `search-index.json` - Search index for fast queries

### 2. Single HTML File

Generates one self-contained HTML file with:
- All documents in a single scrollable page
- Embedded CSS styling
- Base64-encoded images (optional)
- Table of contents with smooth scrolling
- Print-optimized layout

### 3. JSON Export

Exports all document data as structured JSON for:
- Custom visualization tools
- Data analysis pipelines
- API integration
- Database import

## Architecture

```
viewer/
├── aggregator.py      # Document collection and search
├── html_generator.py  # HTML output generation
├── cli.py            # Command-line interface
└── example.py        # Usage examples
```

### Key Classes

- **DocumentAggregator**: Scans cache directory, loads documents, provides search
- **ExtractedDocument**: Represents a single document with its content and metadata
- **UnifiedHTMLGenerator**: Creates HTML outputs in various formats

## Styling and Customization

The generated HTML includes:
- Responsive design for mobile/tablet viewing
- Dark navigation bar with document statistics
- Clean typography optimized for readability
- Hover effects and smooth scrolling
- Print stylesheet that removes navigation

To customize styling, modify the CSS in `html_generator.py::_get_css_content()`.

## Performance Considerations

- **Large Documents**: For collections > 100MB, use `--no-images` flag
- **Search**: Client-side search works well up to ~10,000 blocks
- **Memory**: Single-page HTML can be memory-intensive for very large collections

## Examples

### View Marketing Materials
```bash
python -m src.viewer.cli --cache-dir data/cache --format site --open
```

### Create Printable Report
```bash
python -m src.viewer.cli --format single-html --output report.html
# Then open report.html and print to PDF
```

### Search and Export Results
```python
from src.viewer import DocumentAggregator

aggregator = DocumentAggregator()
results = aggregator.search_content("dosing schedule")

# Export search results
import json
with open("search_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

## Integration with Fact Checking

The viewer can display fact-checking results alongside extracted content:

```python
# Future enhancement: overlay fact-check results
for doc in aggregator.documents:
    fact_check_results = load_fact_check_results(doc.name)
    # Merge with document display
```

## Troubleshooting

**No documents found**: Ensure documents have been processed through ingestion pipeline first
**Images not displaying**: Check that image files exist in `extracted/figures/` directories
**Search not working**: Verify `search-index.json` was generated correctly

## Future Enhancements

- [ ] Fact-check result overlay
- [ ] Document comparison view
- [ ] Export to PDF directly
- [ ] Real-time document updates
- [ ] Collaborative annotations