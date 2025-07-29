#!/usr/bin/env python
"""Quick test script to process a single PDF."""

from pathlib import Path
from src.injestion.pipeline import ingest_pdf

# Process the CDC PDF
pdf_path = Path("./data/clinical_files/CDC Influenza vaccines.pdf")
print(f"Processing: {pdf_path}")

try:
    document = ingest_pdf(pdf_path)
    print(f"✓ Success! Processed {len(document.blocks)} blocks")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()