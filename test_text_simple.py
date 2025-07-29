#!/usr/bin/env python3
"""Simple test to see what text exists vs what's detected"""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import layoutparser as lp
from pdf2image import convert_from_path
import pdfplumber

def main():
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Analyzing: {pdf_path.name}")
    print("=" * 60)
    
    # Extract all text from PDF
    print("\n1. EXTRACTING ALL TEXT FROM PDF")
    print("-" * 40)
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract all text
            page_text = page.extract_text()
            
            # Extract words with positions
            words = page.extract_words()
            
            print(f"\nPage {page_num + 1}:")
            print(f"  - Total words found: {len(words)}")
            print(f"  - Total characters: {len(page_text) if page_text else 0}")
            
            if page_text:
                # Show the actual text content
                print("\n  Text content preview:")
                lines = page_text.split('\n')
                for i, line in enumerate(lines[:20]):  # First 20 lines
                    if line.strip():
                        print(f"    {i+1}: {line.strip()}")
                if len(lines) > 20:
                    print(f"    ... and {len(lines) - 20} more lines")
    
    # Now check what layout detection finds
    print("\n\n2. LAYOUT DETECTION RESULTS")
    print("-" * 40)
    
    images = convert_from_path(str(pdf_path), dpi=400)
    image = images[0]
    
    model = lp.Detectron2LayoutModel(
        "lp://PubLayNet/mask_rcnn_R_50_FPN_3x/config",
        extra_config=[
            "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.1,
            "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.3,
        ],
        label_map={
            0: "Text",
            1: "Title", 
            2: "List",
            3: "Table",
            4: "Figure",
        }
    )
    
    layout = model.detect(image)
    
    # Count text-containing boxes
    text_boxes = [b for b in layout if str(b.type) in ["Text", "Title", "List"]]
    print(f"\nBoxes that might contain text: {len(text_boxes)}")
    print(f"  - Text boxes: {len([b for b in layout if str(b.type) == 'Text'])}")
    print(f"  - Title boxes: {len([b for b in layout if str(b.type) == 'Title'])}")
    print(f"  - List boxes: {len([b for b in layout if str(b.type) == 'List'])}")
    
    print("\n\n3. KEY QUESTION:")
    print("-" * 40)
    print("Are the feature descriptions (e.g., 'The only recombinant flu vaccine...')")
    print("being detected in ANY bounding box?")
    
    # Look for specific text that should be there
    key_phrases = [
        "The only recombinant flu vaccine",
        "Flublok also contains 3x the hemagglutinin",
        "Cell- and egg-based flu vaccines have",
        "Recombinant technology leads to a",
        "According to a study published by the CDC"
    ]
    
    print("\nSearching for key phrases in extracted text...")
    with pdfplumber.open(pdf_path) as pdf:
        page_text = pdf.pages[0].extract_text()
        for phrase in key_phrases:
            if phrase in page_text:
                print(f"  ✓ Found: '{phrase}...'")
            else:
                print(f"  ✗ Missing: '{phrase}...'")

if __name__ == "__main__":
    main()