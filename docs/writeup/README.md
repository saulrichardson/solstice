# Solstice Technical Writeup

This directory contains LaTeX documentation for the Solstice medical fact-checking system.

## Directory Structure

```
writeup/
├── src/              # LaTeX source files
│   └── solstice.tex    # Main 2-page technical document
├── assets/           # Images and figures
│   ├── marketing_layout_example.png
│   └── scientific_layout_example.png
├── solstice.pdf      # Generated PDF
└── build/            # Build artifacts (gitignored)
```

## Building the PDF

```bash
# Build the main writeup
make writeup


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
2. **System Architecture** - Document ingestion and multi-step LLM evidence pipeline
3. **Technical Implementation** - Streamlined orchestration and LLM pipeline design
4. **Key Innovations** - Evidence-based verification, multimodal analysis
5. **Results** - Performance metrics and applications
6. **Future Directions** - Planned enhancements

#### LLM Pipeline Architecture
The fact-checking system uses a streamlined evidence pipeline with specialized LLM processing steps:
- **EvidenceExtractor**: Finds quotes from documents that support claims
- **CompletenessChecker**: Searches for additional supporting quotes not found in initial extraction
- **EvidenceVerifierV2**: Validates that quotes exist in the document and genuinely support claims
- **ImageEvidenceAnalyzer**: Extracts evidence from charts and figures

After LLM processing, an Evidence Presenter (non-LLM) consolidates all verified evidence into the final report.

The ClaimOrchestrator coordinates these LLM steps across multiple documents, maintaining evidence trails with exact quotes and page references.


## Notes

- Build artifacts are kept in `build/` directory
- Final PDF is generated as `solstice.pdf`
- All temporary files are automatically cleaned up
- Images referenced in documents should be placed in `assets/`