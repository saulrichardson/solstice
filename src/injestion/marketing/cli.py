#!/usr/bin/env python
"""Command-line interface for marketing document processing."""

import argparse
import sys
from pathlib import Path

from .pipeline import MarketingPipeline


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Process marketing documents using PrimaLayout detection with advanced consolidation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the marketing PDF document to process"
    )
    
    args = parser.parse_args()
    
    # Validate PDF path
    if not args.pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    if not args.pdf_path.suffix.lower() == '.pdf':
        print(f"Error: File must be a PDF: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    # Create pipeline with marketing preset (no user adjustments)
    pipeline = MarketingPipeline()
    
    print(f"\nProcessing: {args.pdf_path}")
    print("Using marketing-optimized settings (PrimaLayout detection)")
    print("=" * 60)
    
    try:
        # Process the document
        document = pipeline.process_pdf(args.pdf_path)
        
        print(f"\n✓ Processing complete!")
        print(f"  Total blocks: {len(document.blocks)}")
        
        # Show block distribution
        block_types = {}
        for block in document.blocks:
            block_types[block.role] = block_types.get(block.role, 0) + 1
        
        print("\n  Block distribution:")
        for role, count in sorted(block_types.items()):
            print(f"    {role}: {count}")
        
        # Show output location
        output_dir = Path("data/cache") / args.pdf_path.stem / "extracted"
        print(f"\n  Outputs saved to: {output_dir}")
        
        viz_dir = Path("data/cache") / args.pdf_path.stem / "visualizations"
        print(f"  Visualizations saved to: {viz_dir}")
        
    except Exception as e:
        print(f"\n✗ Error processing PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()