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
    parser.add_argument(
        "--overlap-resolution",
        action="store_true",
        help="Enable overlap resolution (default: disabled)"
    )
    parser.add_argument(
        "--no-expand",
        action="store_true",
        help="Disable box expansion (default: enabled with 10px padding)"
    )
    parser.add_argument(
        "--box-padding",
        type=float,
        default=10.0,
        help="Pixels to expand boxes (default: 10.0)"
    )
    parser.add_argument(
        "--merge-threshold",
        type=float,
        default=0.3,
        help="IoU threshold for merging same-type boxes (default: 0.3)"
    )
    
    args = parser.parse_args()
    
    if not args.pdf_path.exists():
        print(f"Error: PDF not found: {args.pdf_path}")
        sys.exit(1)
    
    # Create pipeline
    pipeline = MarketingPipeline(
        use_vision_adjustment=args.vision,
        create_visualizations=not args.no_viz,
        apply_overlap_resolution=args.overlap_resolution,
        expand_boxes=not args.no_expand,
        box_padding=args.box_padding,
        merge_threshold=args.merge_threshold
    )
    
    print(f"Processing: {args.pdf_path.name}")
    print(f"  Vision adjustment: {'enabled' if args.vision else 'disabled'}")
    print(f"  Visualizations: {'enabled' if not args.no_viz else 'disabled'}")
    print(f"  Box expansion: {'enabled' if not args.no_expand else 'disabled'} (padding: {args.box_padding}px)")
    print(f"  Overlap resolution: {'enabled' if args.overlap_resolution else 'disabled'} (merge threshold: {args.merge_threshold})")
    print()
    
    # Process
    document = pipeline.process_pdf(args.pdf_path)
    
    print(f"\nSuccess! Processed {len(document.blocks)} blocks")
    print(f"Outputs saved to: data/cache/{args.pdf_path.stem}/stages/marketing/")


if __name__ == "__main__":
    main()