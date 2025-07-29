#!/usr/bin/env python3
"""Compare what text exists in PDF vs what layout detection captures"""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import layoutparser as lp
from pdf2image import convert_from_path
import pdfplumber
import PyMuPDF as fitz

def extract_text_pypdf2(pdf_path):
    """Extract text using PyPDF2"""
    print("\n=== PyPDF2 Text Extraction ===")
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            text += page_text
            print(f"Page {page_num + 1}: {len(page_text)} characters")
    return text

def extract_text_pdfplumber(pdf_path):
    """Extract text using pdfplumber with bounding boxes"""
    print("\n=== PDFPlumber Text Extraction ===")
    all_text = ""
    text_with_boxes = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text
            page_text = page.extract_text()
            all_text += page_text or ""
            
            # Extract words with bounding boxes
            words = page.extract_words()
            print(f"Page {page_num + 1}: {len(words)} words with bounding boxes")
            
            # Show sample words and their locations
            if words:
                print("  Sample words with locations:")
                for word in words[:5]:
                    print(f"    '{word['text']}' at ({word['x0']:.0f},{word['top']:.0f})")
                if len(words) > 5:
                    print(f"    ... and {len(words) - 5} more words")
                    
            text_with_boxes.extend(words)
    
    return all_text, text_with_boxes

def extract_text_pymupdf(pdf_path):
    """Extract text using PyMuPDF with detailed positioning"""
    print("\n=== PyMuPDF Text Extraction ===")
    doc = fitz.open(pdf_path)
    all_text = ""
    text_blocks = []
    
    for page_num, page in enumerate(doc):
        # Get text
        page_text = page.get_text()
        all_text += page_text
        
        # Get text blocks with positions
        blocks = page.get_text("blocks")
        print(f"Page {page_num + 1}: {len(blocks)} text blocks")
        
        for block in blocks:
            if block[6] == 0:  # text block (not image)
                x0, y0, x1, y1 = block[:4]
                text = block[4]
                text_blocks.append({
                    'bbox': (x0, y0, x1, y1),
                    'text': text.strip()
                })
        
    doc.close()
    return all_text, text_blocks

def compare_with_layout_detection(pdf_path, text_blocks_from_pdf):
    """Compare PDF text extraction with layout detection"""
    print("\n=== Layout Detection Comparison ===")
    
    # Convert to image and run layout detection
    images = convert_from_path(str(pdf_path), dpi=400)
    image = images[0]
    
    # Run layout detection with low threshold
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
    
    # Get all detected regions (not just Text)
    print(f"\nLayout detection found {len(layout)} boxes total")
    
    # Create bounding box coverage map
    detected_regions = []
    for box in layout:
        detected_regions.append({
            'bbox': (box.block.x_1, box.block.y_1, box.block.x_2, box.block.y_2),
            'type': str(box.type)
        })
    
    # Check which text blocks from PDF are covered by layout detection
    covered_text = []
    uncovered_text = []
    
    # Scale factor from PDF coordinates to image coordinates
    # Assuming PDF is 612x792 points and image is 4400x3400 pixels
    scale_x = image.width / 612
    scale_y = image.height / 792
    
    for text_block in text_blocks_from_pdf:
        if not text_block['text'].strip():
            continue
            
        # Convert PDF coordinates to image coordinates
        pdf_bbox = text_block['bbox']
        img_bbox = (
            pdf_bbox[0] * scale_x,
            pdf_bbox[1] * scale_y,
            pdf_bbox[2] * scale_x,
            pdf_bbox[3] * scale_y
        )
        
        # Check if this text is covered by any detected box
        covered = False
        for det_box in detected_regions:
            if bbox_overlap(img_bbox, det_box['bbox']):
                covered = True
                covered_text.append({
                    'text': text_block['text'][:50] + '...' if len(text_block['text']) > 50 else text_block['text'],
                    'covered_by': det_box['type']
                })
                break
        
        if not covered and len(text_block['text'].strip()) > 10:  # Ignore very short text
            uncovered_text.append({
                'text': text_block['text'][:100] + '...' if len(text_block['text']) > 100 else text_block['text'],
                'location': img_bbox
            })
    
    return covered_text, uncovered_text

def bbox_overlap(box1, box2):
    """Check if two bounding boxes overlap"""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    # Check if boxes overlap
    x_overlap = x1_min < x2_max and x1_max > x2_min
    y_overlap = y1_min < y2_max and y1_max > y2_min
    
    return x_overlap and y_overlap

def main():
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Analyzing text coverage for: {pdf_path.name}")
    print("=" * 60)
    
    # Extract text using different methods
    pypdf2_text = extract_text_pypdf2(pdf_path)
    pdfplumber_text, pdfplumber_words = extract_text_pdfplumber(pdf_path)
    pymupdf_text, pymupdf_blocks = extract_text_pymupdf(pdf_path)
    
    # Show sample of extracted text
    print("\n=== Sample Extracted Text ===")
    print("First 500 characters:")
    print(pymupdf_text[:500])
    print("...")
    
    # Compare with layout detection
    covered, uncovered = compare_with_layout_detection(pdf_path, pymupdf_blocks)
    
    print("\n=== COVERAGE ANALYSIS ===")
    print(f"Text blocks covered by layout detection: {len(covered)}")
    print(f"Text blocks NOT covered by any box: {len(uncovered)}")
    
    if uncovered:
        print("\n=== MISSING TEXT (not in any bounding box) ===")
        for i, missing in enumerate(uncovered[:10], 1):
            print(f"\n{i}. Text: {missing['text']}")
            print(f"   Location: {missing['location']}")
        
        if len(uncovered) > 10:
            print(f"\n... and {len(uncovered) - 10} more uncovered text blocks")

if __name__ == "__main__":
    main()