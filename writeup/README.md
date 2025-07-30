# Solstice Technical Writeup

This directory contains a 2-page LaTeX writeup explaining the Solstice medical fact-checking system.

## Building the PDF

```bash
# Build the PDF
make

# View the PDF (macOS)
make view

# Clean auxiliary files
make clean
```

## Requirements

- LaTeX distribution (TeX Live, MiKTeX, or MacTeX)
- pdflatex command available

## Contents

- `solstice.tex` - Main LaTeX document
- `Makefile` - Build automation
- `solstice.pdf` - Generated PDF (after building)

## Key Sections

1. **Introduction** - System overview and purpose
2. **System Architecture** - Document ingestion and multi-agent pipeline
3. **Technical Implementation** - Orchestration, models, and error handling
4. **Key Innovations** - Multimodal analysis, hierarchical verification
5. **Results** - Performance metrics and applications
6. **Future Directions** - Planned enhancements

The writeup is designed to fit exactly 2 pages with high information density while remaining readable.