#!/usr/bin/env python3
"""Compare Tesseract OCR vs PyMuPDF text extraction."""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

sys.path.insert(0, str(Path(__file__).parent))

from src.injestion.processing.text_extractors.tesseract_extractor import TesseractExtractor


class SimplePyMuPDFExtractor:
    """Simple PyMuPDF extractor for comparison."""
    
    def extract_text_from_bbox(self, pdf_path, page_num, bbox, page_height):
        """Extract text using PyMuPDF's built-in method."""
        doc = fitz.open(str(pdf_path))
        page = doc[page_num]
        
        # Get text directly from bbox
        rect = fitz.Rect(bbox)
        text = page.get_textbox(rect)
        
        doc.close()
        
        from src.injestion.processing.text_extractors.base_extractor import ExtractorResult
        return ExtractorResult(
            text=text.strip(),
            confidence=1.0,  # PyMuPDF doesn't provide confidence
            metadata={'method': 'pymupdf'}
        )


def get_test_blocks(pdf_path: Path, num_blocks: int = 5) -> List[Dict]:
    """Get sample text blocks from a PDF for testing."""
    doc = fitz.open(str(pdf_path))
    test_blocks = []
    
    # Get blocks from first few pages
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        blocks = page.get_text("dict")
        
        # Find text blocks with reasonable content
        for block in blocks.get("blocks", []):
            if block.get("type") == 0:  # Text block
                text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "")
                
                # Skip very short blocks
                if len(text.strip()) > 50:
                    test_blocks.append({
                        'page': page_num,
                        'bbox': block['bbox'],
                        'original_text': text.strip(),
                        'page_height': page.rect.height
                    })
                    
                    if len(test_blocks) >= num_blocks:
                        doc.close()
                        return test_blocks
    
    doc.close()
    return test_blocks


def compare_extraction_methods(pdf_path: Path):
    """Compare Tesseract and PyMuPDF extraction methods."""
    
    print(f"Comparing OCR methods on: {pdf_path.name}\n")
    
    # Get test blocks
    test_blocks = get_test_blocks(pdf_path, num_blocks=5)
    if not test_blocks:
        print("No suitable text blocks found!")
        return
    
    print(f"Found {len(test_blocks)} test blocks\n")
    
    # Initialize extractors
    tesseract_extractor = TesseractExtractor()
    pymupdf_extractor = SimplePyMuPDFExtractor()
    
    results = []
    
    for i, block in enumerate(test_blocks):
        print(f"Testing block {i+1}/{len(test_blocks)}...")
        print(f"  Page: {block['page']}, BBox: {[round(x, 1) for x in block['bbox']]}")
        print(f"  Original text preview: {block['original_text'][:100]}...")
        
        # Test Tesseract
        start_time = time.time()
        tesseract_result = tesseract_extractor.extract_text_from_bbox(
            pdf_path,
            block['page'],
            block['bbox'],
            block['page_height']
        )
        tesseract_time = time.time() - start_time
        
        # Test PyMuPDF
        start_time = time.time()
        pymupdf_result = pymupdf_extractor.extract_text_from_bbox(
            pdf_path,
            block['page'],
            block['bbox'],
            block['page_height']
        )
        pymupdf_time = time.time() - start_time
        
        # Calculate similarity
        def calculate_similarity(text1: str, text2: str) -> float:
            """Simple character-based similarity."""
            if not text1 or not text2:
                return 0.0
            
            # Normalize texts
            t1 = text1.lower().replace(" ", "").replace("\n", "")
            t2 = text2.lower().replace(" ", "").replace("\n", "")
            
            # Character overlap
            common = sum(1 for c1, c2 in zip(t1, t2) if c1 == c2)
            return common / max(len(t1), len(t2))
        
        tesseract_similarity = calculate_similarity(block['original_text'], tesseract_result.text)
        pymupdf_similarity = calculate_similarity(block['original_text'], pymupdf_result.text)
        
        result = {
            'block_num': i + 1,
            'tesseract': {
                'text': tesseract_result.text,
                'confidence': tesseract_result.confidence,
                'time': tesseract_time,
                'similarity': tesseract_similarity,
                'length': len(tesseract_result.text)
            },
            'pymupdf': {
                'text': pymupdf_result.text,
                'confidence': pymupdf_result.confidence,
                'time': pymupdf_time,
                'similarity': pymupdf_similarity,
                'length': len(pymupdf_result.text)
            },
            'original_length': len(block['original_text'])
        }
        
        results.append(result)
        
        print(f"  Tesseract: {len(tesseract_result.text)} chars, {tesseract_time:.2f}s, "
              f"confidence: {tesseract_result.confidence:.2f}, similarity: {tesseract_similarity:.2f}")
        print(f"  PyMuPDF:   {len(pymupdf_result.text)} chars, {pymupdf_time:.2f}s, "
              f"confidence: {pymupdf_result.confidence:.2f}, similarity: {pymupdf_similarity:.2f}")
        print()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    # Average metrics
    avg_tesseract_conf = sum(r['tesseract']['confidence'] for r in results) / len(results)
    avg_pymupdf_conf = sum(r['pymupdf']['confidence'] for r in results) / len(results)
    
    avg_tesseract_time = sum(r['tesseract']['time'] for r in results) / len(results)
    avg_pymupdf_time = sum(r['pymupdf']['time'] for r in results) / len(results)
    
    avg_tesseract_sim = sum(r['tesseract']['similarity'] for r in results) / len(results)
    avg_pymupdf_sim = sum(r['pymupdf']['similarity'] for r in results) / len(results)
    
    print(f"\nAverage Confidence:")
    print(f"  Tesseract: {avg_tesseract_conf:.2f}")
    print(f"  PyMuPDF:   {avg_pymupdf_conf:.2f}")
    
    print(f"\nAverage Time per Block:")
    print(f"  Tesseract: {avg_tesseract_time:.3f}s")
    print(f"  PyMuPDF:   {avg_pymupdf_time:.3f}s")
    
    print(f"\nAverage Similarity to Original:")
    print(f"  Tesseract: {avg_tesseract_sim:.2f}")
    print(f"  PyMuPDF:   {avg_pymupdf_sim:.2f}")
    
    # Show a detailed comparison of one block
    print("\n" + "="*60)
    print("DETAILED COMPARISON OF BLOCK 1")
    print("="*60)
    
    if results:
        r = results[0]
        print(f"\nOriginal text ({r['original_length']} chars):")
        print("-" * 40)
        print(test_blocks[0]['original_text'][:300] + "...")
        
        print(f"\nTesseract result ({r['tesseract']['length']} chars):")
        print("-" * 40)
        print(r['tesseract']['text'][:300] + "...")
        
        print(f"\nPyMuPDF result ({r['pymupdf']['length']} chars):")
        print("-" * 40)
        print(r['pymupdf']['text'][:300] + "...")
    
    # Save results
    output_file = Path("ocr_comparison_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")


def main():
    """Main entry point."""
    # Check if Tesseract is installed
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract version: {version}")
    except Exception as e:
        print(f"Error: Tesseract not found. Please install it first:")
        print("  brew install tesseract")
        return 1
    
    # Use a test PDF
    test_pdf = Path("data/clinical_files/FlublokPI.pdf")
    if not test_pdf.exists():
        print(f"Test PDF not found: {test_pdf}")
        return 1
    
    compare_extraction_methods(test_pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())