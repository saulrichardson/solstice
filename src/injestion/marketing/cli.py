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
    
    # Detection settings
    detection_group = parser.add_argument_group("Detection Settings")
    detection_group.add_argument(
        "--score-threshold",
        type=float,
        default=0.15,
        help="Detection confidence threshold"
    )
    detection_group.add_argument(
        "--nms-threshold",
        type=float,
        default=0.4,
        help="Non-maximum suppression threshold"
    )
    detection_group.add_argument(
        "--detection-dpi",
        type=int,
        default=400,
        help="DPI for PDF rasterization"
    )
    
    # Consolidation settings
    consolidation_group = parser.add_argument_group("Box Consolidation Settings")
    consolidation_group.add_argument(
        "--no-overlap-resolution",
        action="store_true",
        help="Disable overlap resolution (not recommended)"
    )
    consolidation_group.add_argument(
        "--no-expand-boxes",
        action="store_true",
        help="Disable box expansion for text cutoff prevention"
    )
    consolidation_group.add_argument(
        "--box-padding",
        type=float,
        default=10.0,
        help="Pixels to expand boxes in each direction"
    )
    consolidation_group.add_argument(
        "--merge-threshold",
        type=float,
        default=0.2,
        help="IoU threshold for merging same-type boxes (0.2 = 20%% overlap)"
    )
    
    # Preset configurations
    parser.add_argument(
        "--preset",
        choices=["default", "aggressive", "conservative"],
        help="Use preset configuration (overrides individual settings)"
    )
    
    args = parser.parse_args()
    
    # Validate PDF path
    if not args.pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    if not args.pdf_path.suffix.lower() == '.pdf':
        print(f"Error: File must be a PDF: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    # Apply presets if specified
    if args.preset == "aggressive":
        print("Using aggressive consolidation preset...")
        args.merge_threshold = 0.1
        args.box_padding = 15.0
    elif args.preset == "conservative":
        print("Using conservative preset...")
        args.merge_threshold = 0.5
        args.box_padding = 5.0
        args.no_expand_boxes = True
    
    # Create config from CLI arguments
    from ..config import get_config
    
    # Start with marketing preset
    config = get_config('marketing')
    
    # Override with CLI arguments
    config = config.__class__(
        score_threshold=args.score_threshold,
        nms_threshold=args.nms_threshold,
        detection_dpi=args.detection_dpi,
        merge_overlapping=not args.no_overlap_resolution,
        expand_boxes=not args.no_expand_boxes,
        box_padding=args.box_padding,
        merge_threshold=args.merge_threshold,
        confidence_weight=config.confidence_weight,
        area_weight=config.area_weight,
        create_visualizations=config.create_visualizations,
        apply_text_processing=config.apply_text_processing,
        minor_overlap_threshold=config.minor_overlap_threshold
    )
    
    # Initialize pipeline with config
    pipeline = MarketingPipeline(config=config)
    
    print(f"\nProcessing: {args.pdf_path}")
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
        output_dir = Path("data/cache") / args.pdf_path.stem / "marketing"
        print(f"\n  Outputs saved to: {output_dir}")
        
        viz_dir = Path("data/cache") / args.pdf_path.stem / "visualizations"
        print(f"  Visualizations saved to: {viz_dir}")
        
    except Exception as e:
        print(f"\n✗ Error processing PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()