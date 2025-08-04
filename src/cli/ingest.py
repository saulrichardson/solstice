#!/usr/bin/env python3
"""Zero-configuration PDF ingestion CLI.

Processes all PDFs in data/clinical_files/ with optimized settings for clinical documents.
"""

import sys
from pathlib import Path
from typing import Optional

from ..injestion.scientific.standard_pipeline import StandardPipeline
from ..injestion.shared.config import get_config


# Default paths
DEFAULT_INPUT_DIR = Path("data/clinical_files")


def process_all_pdfs(output_dir: Optional[Path] = None) -> None:
    """Process all PDFs in the default clinical files directory.
    
    Args:
        output_dir: Optional custom output directory. If None, uses default.
    """
    
    # Create pipeline with clinical preset (or custom config for output_dir)
    if output_dir is not None:
        config = get_config('clinical')
        # Create a modified config with custom cache directory
        from dataclasses import replace
        config = replace(config, cache_dir=str(output_dir))
        pipeline = StandardPipeline(config)
        cache_dir = output_dir
    else:
        config = get_config('clinical')
        pipeline = StandardPipeline(config)
        cache_dir = Path(pipeline.config.cache_dir)
    
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
        
        try:
            # Run ingestion pipeline with optimized settings
            document = pipeline.process_pdf(pdf_path)
            
            print(f"✓ Successfully processed {pdf_path.name}")
            total_pages = document.metadata.get("total_pages", "?")
            print(f"  - Total pages: {total_pages}")
            print(f"  - Total blocks detected: {len(document.blocks)}")
            print(f"  - Text extractor: PyMuPDF")
            
            successful += 1
        except Exception as e:
            print(f"✗ Failed to process {pdf_path.name}: {e}")
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"  - Successful: {successful}")
    print(f"  - Failed: {failed}")
    print(f"  - Results saved in: {cache_dir}/")


def main(output_dir=None):
    """Main CLI entrypoint."""
    # Run the batch processing
    process_all_pdfs(output_dir=output_dir)


