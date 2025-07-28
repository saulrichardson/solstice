#!/usr/bin/env python3
"""Zero-configuration PDF ingestion CLI.

Processes all PDFs in data/clinical_files/ with optimized settings for clinical documents.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from ..injestion import ingest_pdf
from ..injestion.storage.paths import set_cache_root


# Default paths
DEFAULT_INPUT_DIR = Path("data/clinical_files")
DEFAULT_OUTPUT_DIR = Path("data/cache")


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
        
        try:
            # Run ingestion pipeline with optimized settings
            document = ingest_pdf(pdf_path)
            
            print(f"✓ Successfully processed {pdf_path.name}")
            total_pages = document.metadata.get("total_pages", "?")
            print(f"  - Total pages: {total_pages}")
            print(f"  - Total blocks detected: {len(document.blocks)}")
            
            successful += 1
            
        except Exception as e:
            print(f"✗ Error processing {pdf_path.name}: {e}")
            failed += 1
            # Continue processing other files
    
    # Summary
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"  - Successful: {successful}")
    print(f"  - Failed: {failed}")
    print(f"  - Results saved in: {output_dir}/")


def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Process clinical PDFs with optimized layout detection and text extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Default behavior:
  - Processes all PDFs in: data/clinical_files/
  - Saves results to: data/cache/
  - Uses optimized settings for clinical documents (400 DPI, merge overlapping, etc.)
  
Example:
  python -m cli.ingest
  python -m cli.ingest --output-dir /custom/output/path
        """
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=f"Custom output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    
    args = parser.parse_args()
    
    # Run the batch processing
    process_all_pdfs(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
