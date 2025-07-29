#!/usr/bin/env python3
"""Test layout detection and extraction on Flublok marketing PDF."""

import sys
from pathlib import Path
sys.path.insert(0, "src")

from injestion.pipeline import ingest_pdf

def main():
    # Path to your marketing PDF
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Processing: {pdf_path.name}")
    print("-" * 50)
    
    # Run the full ingestion pipeline
    document = ingest_pdf(pdf_path)
    
    # Print summary
    print(f"\nDetected {len(document.blocks)} blocks")
    print("\nBlocks by type:")
    
    # Group by role
    by_role = {}
    for block in document.blocks:
        by_role.setdefault(block.role, []).append(block)
    
    for role, blocks in sorted(by_role.items()):
        print(f"  {role}: {len(blocks)} blocks")
    
    # Show first few text blocks
    print("\nSample extracted text:")
    print("-" * 50)
    text_blocks = [b for b in document.blocks if b.role == "Text" and b.text][:3]
    for i, block in enumerate(text_blocks, 1):
        print(f"{i}. {block.text[:100]}..." if len(block.text) > 100 else f"{i}. {block.text}")
    
    # Output locations
    cache_dir = Path("data/cache/FlublokOnePage")
    print(f"\nOutputs saved to: {cache_dir}")
    print(f"  - Visualizations: {cache_dir}/stages/raw_layouts/visualizations/")
    print(f"  - Extracted text: {cache_dir}/stages/extracted/document.md")
    print(f"  - HTML version: {cache_dir}/stages/extracted/document.html")

if __name__ == "__main__":
    main()