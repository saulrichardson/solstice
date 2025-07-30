#!/usr/bin/env python3
"""CLI for marketing document ingestion."""

import argparse
import sys
from pathlib import Path

from ..injestion.marketing import MarketingPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Process marketing PDFs with PrimaLayout detection"
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to marketing PDF file"
    )
    
    args = parser.parse_args()
    
    if not args.pdf_path.exists():
        print(f"Error: PDF not found: {args.pdf_path}")
        sys.exit(1)
    
    # Create pipeline with marketing preset
    pipeline = MarketingPipeline()
    
    print(f"Processing: {args.pdf_path.name}")
    print(f"Using marketing-optimized settings")
    print()
    
    # Process
    document = pipeline.process_pdf(args.pdf_path)
    
    print(f"\nSuccess! Processed {len(document.blocks)} blocks")
    print(f"Outputs saved to: data/cache/{args.pdf_path.stem}/extracted/")


if __name__ == "__main__":
    main()