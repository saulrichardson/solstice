#!/usr/bin/env python3
"""Run the marketing pipeline on a PDF."""

import sys
from pathlib import Path
sys.path.insert(0, "src")

from injestion.marketing import MarketingPipeline


def main():
    # Your marketing PDF
    pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
    
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    print(f"Processing marketing PDF: {pdf_path.name}")
    print("-" * 60)
    
    # Create pipeline (without vision adjustment for now)
    pipeline = MarketingPipeline(
        use_vision_adjustment=False,  # Set to True if you have OPENAI_API_KEY
        create_visualizations=True
    )
    
    # Process the PDF
    document = pipeline.process_pdf(pdf_path)
    
    # Results
    print(f"\nProcessing complete!")
    print(f"Total blocks: {len(document.blocks)}")
    
    # Count by type
    by_type = {}
    for block in document.blocks:
        by_type[block.role] = by_type.get(block.role, 0) + 1
    
    print("\nBlocks by type:")
    for role, count in sorted(by_type.items()):
        print(f"  {role}: {count}")
    
    # Output locations
    print(f"\nOutputs saved to:")
    print(f"  data/cache/{pdf_path.stem}/stages/marketing/")
    print(f"  - document.json: Full document with extracted text")
    print(f"  - summary.json: Processing summary")
    print(f"  - visualizations/: Layout visualizations")


if __name__ == "__main__":
    main()