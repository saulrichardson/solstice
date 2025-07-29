#!/usr/bin/env python3
"""Test Tesseract with different DPI settings."""

import sys
from pathlib import Path
import fitz
import pytesseract
from PIL import Image
import io

sys.path.insert(0, str(Path(__file__).parent))


def test_tesseract_dpi(pdf_path: Path):
    """Test Tesseract with various DPI settings."""
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]  # First page
    
    # Get a text block
    blocks = page.get_text("dict")
    text_block = None
    for block in blocks.get("blocks", []):
        if block.get("type") == 0:  # Text block
            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "")
            
            if len(text.strip()) > 50:
                text_block = block
                break
    
    if not text_block:
        print("No suitable text block found")
        return
    
    bbox = text_block['bbox']
    rect = fitz.Rect(bbox)
    original_text = text.strip()
    
    print(f"Testing text block: {original_text[:100]}...")
    print(f"BBox: {[round(x, 1) for x in bbox]}")
    print(f"Page size: {page.rect.width} x {page.rect.height}")
    print()
    
    # Test different DPI values
    dpi_values = [72, 150, 300, 400, 600]
    
    for dpi in dpi_values:
        print(f"\nTesting DPI: {dpi}")
        
        # Render at specified DPI
        mat = fitz.Matrix(dpi/72.0, dpi/72.0)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        print(f"  Image size: {img.size}")
        
        # Save image for inspection
        img_path = f"tesseract_test_dpi_{dpi}.png"
        img.save(img_path)
        print(f"  Saved to: {img_path}")
        
        # Run Tesseract
        try:
            text = pytesseract.image_to_string(img).strip()
            
            # Calculate similarity
            def similarity(t1, t2):
                if not t1 or not t2:
                    return 0.0
                t1 = t1.lower().replace(" ", "")
                t2 = t2.lower().replace(" ", "")
                common = sum(1 for c1, c2 in zip(t1, t2) if c1 == c2)
                return common / max(len(t1), len(t2))
            
            sim = similarity(original_text, text)
            
            print(f"  Extracted: {text[:100]}...")
            print(f"  Similarity: {sim:.2f}")
            print(f"  Length: {len(text)} chars (original: {len(original_text)})")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    doc.close()
    
    # Also test with preprocessing
    print("\n" + "="*60)
    print("Testing DPI 300 with preprocessing")
    print("="*60)
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    
    # Render at 300 DPI
    mat = fitz.Matrix(300/72.0, 300/72.0)
    pix = page.get_pixmap(matrix=mat, clip=rect)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    # Preprocessing steps
    from PIL import ImageEnhance, ImageOps
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    
    # Sharpen
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)
    
    # Save preprocessed image
    img.save("tesseract_test_preprocessed.png")
    
    # Test with different PSM modes
    psm_modes = [3, 6, 8, 11, 13]
    for psm in psm_modes:
        print(f"\nPSM mode {psm}:")
        try:
            text = pytesseract.image_to_string(img, config=f'--psm {psm}').strip()
            sim = similarity(original_text, text)
            print(f"  Result: {text[:100]}...")
            print(f"  Similarity: {sim:.2f}")
        except Exception as e:
            print(f"  Error: {e}")
    
    doc.close()


if __name__ == "__main__":
    pdf_path = Path("data/clinical_files/FlublokPI.pdf")
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)
    
    test_tesseract_dpi(pdf_path)