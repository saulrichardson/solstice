#!/usr/bin/env python3
"""Extract text from PDF to understand the actual layout"""

import fitz  # PyMuPDF
from pathlib import Path

def extract_page_text(pdf_path, page_num=1):
    """Extract text and layout information from a PDF page"""
    
    pdf = fitz.open(pdf_path)
    page = pdf[page_num - 1]
    
    # Get page dimensions
    print(f"Page dimensions: {page.rect.width} x {page.rect.height}")
    print("=" * 60)
    
    # Extract text blocks with positions
    blocks = page.get_text("blocks")
    
    print(f"Found {len(blocks)} text blocks on page {page_num}:\n")
    
    for i, block in enumerate(blocks):
        x0, y0, x1, y1, text, block_no, block_type = block
        if block_type == 0:  # Text block
            print(f"Block {i+1} ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f}):")
            print(f"  Text: {text[:100]}..." if len(text) > 100 else f"  Text: {text}")
            print()
    
    # Also extract as dict for more structure
    text_dict = page.get_text("dict")
    
    print("\nDetailed structure:")
    print("=" * 60)
    
    for block_idx, block in enumerate(text_dict["blocks"]):
        if block["type"] == 0:  # Text block
            print(f"\nBlock {block_idx + 1}:")
            for line in block["lines"]:
                for span in line["spans"]:
                    print(f"  Font: {span['font']}, Size: {span['size']:.1f}")
                    print(f"  Bbox: ({span['bbox'][0]:.1f}, {span['bbox'][1]:.1f}, {span['bbox'][2]:.1f}, {span['bbox'][3]:.1f})")
                    print(f"  Text: {span['text']}")
    
    pdf.close()

if __name__ == "__main__":
    # First check if PyMuPDF is installed
    try:
        import fitz
        extract_page_text("Liu et al. (2024).pdf", page_num=1)
    except ImportError:
        print("PyMuPDF not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "PyMuPDF"], check=True)
        print("\nNow extracting text...")
        import fitz
        extract_page_text("Liu et al. (2024).pdf", page_num=1)