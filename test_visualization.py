#!/usr/bin/env python3
"""Test visualization functionality."""

from pathlib import Path
from src.injestion import ingest_pdf, visualize_pipeline_results

# Process a PDF with visualizations
pdf_path = Path("input/Clinical Files/Arunachalam et al. (2021).pdf")

if pdf_path.exists():
    print(f"Processing: {pdf_path.name}")
    
    # Run pipeline with visualizations
    doc = ingest_pdf(
        pdf_path,
        create_visualizations=True,
        viz_pages=[0, 1, 2]  # Visualize first 3 pages
    )
    
    print(f"✅ Processed {len(doc.blocks)} elements")
    print(f"📊 Visualizations saved in: data/cache/visualizations/")
    
    # Or visualize an already processed PDF
    # viz_paths = visualize_pipeline_results(pdf_path, pages_to_show=[0, 1])
else:
    print(f"PDF not found: {pdf_path}")