#!/usr/bin/env python3
"""Zero-configuration PDF ingestion CLI.

Processes all PDFs in data/clinical_files/ with optimized settings for clinical documents.
"""

import sys
from pathlib import Path
from typing import Optional

from ..injestion.scientific.pipeline import ingest_pdf
from ..injestion.shared.storage.paths import set_cache_root
from ..core.config import settings


# Default paths
DEFAULT_INPUT_DIR = Path("data/clinical_files")
DEFAULT_OUTPUT_DIR = Path("data/scientific_cache")


def process_all_pdfs(output_dir: Optional[Path] = None) -> None:
    """Process all PDFs in the default clinical files directory.
    
    Args:
        output_dir: Optional custom output directory. If None, uses default.
    """
        
    # Use default output directory if not specified
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    # Ensure the pipeline writes to the requested directory
    # (no-op if *output_dir* equals the default)
    set_cache_root(output_dir)
    
    # Check if input directory exists
    if not DEFAULT_INPUT_DIR.exists():
        print(f"Error: Input directory not found: {DEFAULT_INPUT_DIR}")
        print(f"Please create the directory and add PDF files to process.")
        sys.exit(1)
    
    # Find all PDFs in the input directory (sorted for determinism)
    pdf_files = sorted(DEFAULT_INPUT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {DEFAULT_INPUT_DIR}")
        return
    
    print(f"Found {len(pdf_files)} PDFs to process:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()
    
    # Process statistics
    successful = 0
    failed = 0
    
    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"Processing [{i}/{len(pdf_files)}]: {pdf_path.name}")
        print(f"{'='*60}")
        # Run ingestion pipeline with optimized settings
        document = ingest_pdf(pdf_path)
        
        print(f"✓ Successfully processed {pdf_path.name}")
        total_pages = document.metadata.get("total_pages", "?")
        print(f"  - Total pages: {total_pages}")
        print(f"  - Total blocks detected: {len(document.blocks)}")
        print(f"  - Text extractor: PyMuPDF")
        
        successful += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"  - Successful: {successful}")
    print(f"  - Failed: {failed}")
    print(f"  - Results saved in: {output_dir}/")


def main(output_dir=None):
    """Main CLI entrypoint."""
    # Run the batch processing
    process_all_pdfs(output_dir=output_dir)


