#!/usr/bin/env python3
"""CLI for marketing document ingestion."""

import sys
from pathlib import Path

from ..injestion.marketing import MarketingPipeline
from ..injestion.shared.storage.paths import set_cache_root


def main(pdf_path, output_dir=None):
    """Main entry point.
    
    Args:
        pdf_path: Path to marketing PDF file
        output_dir: Optional custom output directory
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)
    
    # Set custom output directory if provided
    if output_dir is not None:
        set_cache_root(output_dir)
        cache_dir = Path(output_dir)
    else:
        cache_dir = Path("data/cache")
    
    # Create pipeline with marketing preset
    pipeline = MarketingPipeline()
    
    print(f"Processing: {pdf_path.name}")
    print(f"Using marketing-optimized settings")
    print()
    
    # Process
    document = pipeline.process_pdf(pdf_path)
    
    print(f"\nSuccess! Processed {len(document.blocks)} blocks")
    print(f"Outputs saved to: {cache_dir}/{pdf_path.stem}/extracted/")


