#!/usr/bin/env python3
"""CLI for marketing document ingestion."""

import sys
from pathlib import Path
from typing import Optional

from ..injestion.marketing import MarketingPipeline


# Default paths
DEFAULT_INPUT_DIR = Path("data/marketing_slide")


def process_single_pdf(pdf_path: Path, pipeline: MarketingPipeline, cache_dir: Path) -> bool:
    """Process a single marketing PDF.
    
    Args:
        pdf_path: Path to PDF file
        pipeline: MarketingPipeline instance
        cache_dir: Output cache directory
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Processing: {pdf_path.name}")
        document = pipeline.process_pdf(pdf_path)
        print(f"✓ Success! Processed {len(document.blocks)} blocks")
        print(f"  Outputs saved to: {cache_dir}/{pdf_path.stem}/extracted/")
        return True
    except Exception as e:
        print(f"✗ Failed to process {pdf_path.name}: {e}")
        return False


def main(pdf_path=None, output_dir=None):
    """Main entry point.
    
    Args:
        pdf_path: Optional path to marketing PDF file. If None, processes all PDFs in default directory
        output_dir: Optional custom output directory
    """
    # Create pipeline with marketing defaults (or custom cache dir)
    if output_dir is not None:
        pipeline = MarketingPipeline(cache_dir=str(output_dir))
        cache_dir = Path(output_dir)
    else:
        pipeline = MarketingPipeline()  # Uses optimized defaults
        cache_dir = Path(pipeline.cache_dir)
    
    print(f"Using marketing-optimized settings")
    print(f"Cache directory: {cache_dir}")
    print()
    
    # If specific PDF provided, process just that one
    if pdf_path is not None:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            print(f"Error: PDF not found: {pdf_path}")
            sys.exit(1)
        
        success = process_single_pdf(pdf_path, pipeline, cache_dir)
        sys.exit(0 if success else 1)
    
    # Otherwise, process all PDFs in default directory
    if not DEFAULT_INPUT_DIR.exists():
        print(f"Error: Input directory not found: {DEFAULT_INPUT_DIR}")
        print(f"Please create the directory and add marketing PDF files to process.")
        sys.exit(1)
    
    # Find all PDFs in the input directory (sorted for determinism)
    pdf_files = sorted(DEFAULT_INPUT_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {DEFAULT_INPUT_DIR}")
        return
    
    print(f"Found {len(pdf_files)} marketing PDFs to process:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()
    
    # Process statistics
    successful = 0
    failed = 0
    
    # Process each PDF
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"Processing [{i}/{len(pdf_files)}]: {pdf_file.name}")
        print(f"{'='*60}")
        
        if process_single_pdf(pdf_file, pipeline, cache_dir):
            successful += 1
        else:
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("Marketing ingestion complete!")
    print(f"  - Successful: {successful}")
    print(f"  - Failed: {failed}")
    print(f"  - Results saved in: {cache_dir}/")


