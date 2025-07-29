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
    parser.add_argument(
        "--vision",
        action="store_true",
        help="Enable vision LLM adjustments (requires OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization generation"
    )
    
    args = parser.parse_args()
    
    if not args.pdf_path.exists():
        print(f"Error: PDF not found: {args.pdf_path}")
        sys.exit(1)
    
    # Create pipeline
    pipeline = MarketingPipeline(
        use_vision_adjustment=args.vision,
        create_visualizations=not args.no_viz
    )
    
    print(f"Processing: {args.pdf_path.name}")
    print(f"  Vision adjustment: {'enabled' if args.vision else 'disabled'}")
    print(f"  Visualizations: {'enabled' if not args.no_viz else 'disabled'}")
    print()
    
    # Process
    document = pipeline.process_pdf(args.pdf_path)
    
    print(f"\nSuccess! Processed {len(document.blocks)} blocks")
    print(f"Outputs saved to: data/cache/{args.pdf_path.stem}/stages/marketing/")


if __name__ == "__main__":
    main()