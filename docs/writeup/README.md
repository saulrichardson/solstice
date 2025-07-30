# Solstice Technical Writeup

This directory contains LaTeX documentation for the Solstice medical fact-checking system.

## Directory Structure

```
writeup/
├── src/              # LaTeX source files
│   ├── solstice.tex    # Main 2-page technical document
│   ├── solstice_v2.tex # Extended version
│   └── stats.tex       # Performance statistics
├── assets/           # Images and figures
│   ├── marketing_layout_example.png
│   └── scientific_layout_example.png
├── scripts/          # Analysis scripts
│   ├── analyze_cache.py
│   └── cache_stats.json
├── output/           # Generated PDFs
│   └── solstice.pdf
├── build/            # Build artifacts (gitignored)
└── Makefile          # Build automation
```

## Building the PDF

```bash
# Build the main writeup
make writeup

# Build statistics document
make stats

# View the PDF (macOS)
make view

# Clean build artifacts
make clean

# Clean everything including PDFs
make distclean
```

## Requirements

- LaTeX distribution (TeX Live, MiKTeX, or MacTeX)
- pdflatex command available

## Document Overview

### Main Writeup (`solstice.tex`)
A concise 2-page technical summary covering:
1. **Introduction** - System overview and purpose
2. **System Architecture** - Document ingestion and multi-agent evidence pipeline
3. **Technical Implementation** - Streamlined orchestration and agent design
4. **Key Innovations** - Evidence-based verification, multimodal analysis
5. **Results** - Performance metrics and applications
6. **Future Directions** - Planned enhancements

#### Agent Pipeline Architecture
The fact-checking system uses a streamlined evidence pipeline with specialized agents:
- **EvidenceExtractor**: Finds relevant passages from documents
- **CompletenessChecker**: Ensures all aspects of claims are addressed
- **EvidenceVerifierV2**: Validates that evidence actually supports claims
- **ImageEvidenceAnalyzer**: Extracts evidence from charts and figures
- **EvidencePresenter**: Synthesizes final evidence presentation

The ClaimOrchestrator coordinates these agents across multiple documents, maintaining evidence trails with exact quotes and page references.

### Extended Version (`solstice_v2.tex`)
Expanded technical documentation with additional implementation details.

### Statistics (`stats.tex`)
Performance analysis and benchmarking results.

## Notes

- Build artifacts are kept in `build/` directory
- Final PDFs are copied to `output/`
- All temporary files are automatically cleaned up
- Images referenced in documents should be placed in `assets/`