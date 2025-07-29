#!/usr/bin/env python
"""Debug script to find which PDFs are failing."""

from pathlib import Path
from src.injestion.pipeline import ingest_pdf

# Get all PDFs
pdf_dir = Path("./data/clinical_files/")
pdf_files = sorted(pdf_dir.glob("*.pdf"))

print(f"Found {len(pdf_files)} PDFs to process\n")

for pdf_path in pdf_files:
    print(f"Processing: {pdf_path.name}", flush=True)
    document = ingest_pdf(pdf_path)
    print(f"  ✓ Success! {len(document.blocks)} blocks\n", flush=True)