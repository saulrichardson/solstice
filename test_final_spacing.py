#!/usr/bin/env python3
"""Test the final spacing fixer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.injestion.processing.text_extractors.final_spacing_fixer import fix_pdf_text_spacing


def test_final_fixer():
    """Test the final spacing fixer."""
    
    print("FINAL SPACING FIXER TEST")
    print("=" * 80)
    
    test_cases = [
        ("Thesehighlightsdonot includeall theinformationneededtouseFlublok®safely",
         "These highlights do not include all the information needed to use Flublok® safely"),
        
        ("HIGHLIGHTS OF PRESCRIBING INFORMATIONThesehighlightsdonot",
         "HIGHLIGHTS OF PRESCRIBING INFORMATION These highlights do not"),
        
        ("Flublok (Influenza Vaccine)Injection for Intramuscular Use2024-2025",
         "Flublok (Influenza Vaccine) Injection for Intramuscular Use 2024-2025"),
        
        ("safelyand effectively.See full prescribing",
         "safely and effectively. See full prescribing"),
        
        ("18years of age and older",
         "18 years of age and older"),
        
        ("0.5mL",
         "0.5 mL"),
    ]
    
    for original, expected in test_cases:
        fixed = fix_pdf_text_spacing(original)
        
        print(f"\nOriginal: {original}")
        print(f"Fixed:    {fixed}")
        print(f"Expected: {expected}")
        
        # Check if it matches expected
        match = fixed.lower() == expected.lower()
        print(f"Match:    {'✓' if match else '✗'}")


def test_real_data():
    """Test with real PyMuPDF data."""
    
    print("\n" + "=" * 80)
    print("REAL DATA TEST")
    print("=" * 80)
    
    import json
    
    if Path('ocr_comparison_results.json').exists():
        with open('ocr_comparison_results.json', 'r') as f:
            results = json.load(f)
        
        # First block
        pymupdf_text = results[0]['pymupdf']['text']
        tesseract_text = results[0]['tesseract']['text']
        
        fixed = fix_pdf_text_spacing(pymupdf_text)
        
        print("\nOriginal PyMuPDF:")
        print(pymupdf_text[:200] + "...")
        
        print("\nFixed:")
        print(fixed[:200] + "...")
        
        print("\nTesseract (reference):")
        print(tesseract_text[:200] + "...")
        
        # Word comparison
        fixed_words = fixed.lower().split()
        tesseract_words = tesseract_text.lower().split()
        
        matches = 0
        for i, (f, t) in enumerate(zip(fixed_words[:20], tesseract_words[:20])):
            if f == t:
                matches += 1
                print(f"✓ {f}")
            else:
                print(f"✗ {f} != {t}")
        
        print(f"\nFirst 20 words match: {matches}/20 = {matches/20:.0%}")


if __name__ == "__main__":
    test_final_fixer()
    test_real_data()