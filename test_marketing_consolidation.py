#!/usr/bin/env python3
"""Test the marketing pipeline consolidation."""

from pathlib import Path
from src.injestion.marketing.pipeline import MarketingPipeline

def test_consolidation():
    """Test the marketing pipeline with consolidation enabled."""
    # Create pipeline with overlap resolution enabled (now default)
    pipeline = MarketingPipeline(
        use_vision_adjustment=False,  # Skip vision for faster testing
        create_visualizations=True
    )
    
    # Process the test document
    pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
    print(f"Processing {pdf_path}...")
    
    document = pipeline.process_pdf(pdf_path)
    
    print(f"\nProcessed document with {len(document.blocks)} blocks")
    print(f"Blocks by type:")
    type_counts = {}
    for block in document.blocks:
        role = block.role
        type_counts[role] = type_counts.get(role, 0) + 1
    
    for role, count in sorted(type_counts.items()):
        print(f"  {role}: {count}")

if __name__ == "__main__":
    test_consolidation()