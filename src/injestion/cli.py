#!/usr/bin/env python3
"""CLI for PDF ingestion pipeline."""

import argparse
import json
import sys
from pathlib import Path

from .pipeline import ingest_pdf
from .storage.paths import final_doc_path


def main():
    parser = argparse.ArgumentParser(
        description="Ingest PDF files and extract structured content"
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the PDF file to ingest"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="DPI for PDF to image conversion (default: 300)"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output path for the extracted content JSON (default: auto-generated)"
    )
    
    args = parser.parse_args()
    
    # Check if PDF exists
    if not args.pdf_path.exists():
        print(f"Error: PDF file not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing PDF: {args.pdf_path}")
    print(f"DPI: {args.dpi}")
    
    try:
        # Run ingestion with standard settings
        document = ingest_pdf(
            pdf_path=args.pdf_path,
            detection_dpi=args.dpi
        )
        
        # Get output path
        if args.output:
            output_path = args.output
        else:
            # Generate a default output filename based on input
            output_name = args.pdf_path.stem + "_extracted.json"
            output_path = Path(output_name)
        
        # Display extracted content summary
        print("\nExtracted Content Summary:")
        text_blocks = sum(1 for b in document.blocks if b.text and b.role not in ['Figure', 'Table'])
        figure_blocks = sum(1 for b in document.blocks if b.role in ['Figure', 'Table'])
        
        for page_idx in range(document.metadata.get('total_pages', 0)):
            print(f"\nPage {page_idx + 1}:")
            # Get blocks for this page in reading order
            page_blocks = {b.id: b for b in document.blocks if b.page_index == page_idx}
            
            if hasattr(document, 'reading_order') and page_idx < len(document.reading_order):
                order = document.reading_order[page_idx]
                for position, block_id in enumerate(order, 1):
                    if block_id in page_blocks:
                        block = page_blocks[block_id]
                        if block.text:
                            # Show first 80 chars of text
                            text_preview = block.text[:80].replace('\n', ' ')
                            if len(block.text) > 80:
                                text_preview += "..."
                            print(f"  {position}. {block.role}: {text_preview}")
                        else:
                            print(f"  {position}. {block.role} [no text extracted]")
        
        # Save output
        doc_dict = document.model_dump()
        output = json.dumps(doc_dict, indent=2)
        
        if args.output:
            output_path.write_text(output)
            print(f"\n✓ Output saved to {output_path}")
        else:
            # Default: save with auto-generated name
            output_path.write_text(output)
            print(f"\n✓ Output saved to {output_path}")
        
        # Summary statistics
        total_blocks = len(document.blocks)
        total_pages = document.metadata.get('total_pages', 0)
        
        # Show visualization path
        from .storage.paths import doc_id, stage_dir
        viz_dir = stage_dir("visualizations", args.pdf_path)
        
        print(f"\n✓ Processing complete!")
        print(f"  Pages: {total_pages}")
        print(f"  Total blocks: {total_blocks}")
        print(f"  Text blocks: {text_blocks}")
        print(f"  Figures/Tables: {figure_blocks}")
        print(f"  Visualizations: {viz_dir}/")
        print(f"  Extracted content: {stage_dir('extracted', args.pdf_path)}/")
        
    except Exception as e:
        print(f"Error processing PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()