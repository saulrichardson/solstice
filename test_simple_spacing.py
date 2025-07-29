#!/usr/bin/env python3
"""Test the simple spacing fixer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.injestion.processing.text_extractors.smart_spacing_fixer import SmartSpacingFixer, fix_pharmaceutical_text_spacing


def test_spacing_fixes():
    """Test spacing fixes on real examples."""
    
    # Real examples from the PDF
    test_cases = [
        ("Thesehighlightsdonot includeall theinformationneededtouseFlublok®safely",
         "These highlights do not include all the information needed to use Flublok® safely"),
        
        ("HIGHLIGHTS OF PRESCRIBING INFORMATIONThesehighlightsdonot",
         "HIGHLIGHTS OF PRESCRIBING INFORMATION These highlights do not"),
        
        ("Flublok (Influenza Vaccine)Injection for Intramuscular Use2024-2025 FormulaInitial U.S. Approval:2013",
         "Flublok (Influenza Vaccine) Injection for Intramuscular Use 2024-2025 Formula Initial U.S. Approval: 2013"),
        
        ("For intramuscular use(0.5 mL).(2)",
         "For intramuscular use (0.5 mL). (2)"),
        
        ("• Do not administer Flublokto anyone with ahistory of severe",
         "• Do not administer Flublok to anyone with a history of severe"),
        
        ("———————————INDICATIONS AND USAGE———————————Flublok is avaccine indicated",
         "——————————— INDICATIONS AND USAGE ——————————— Flublok is a vaccine indicated"),
    ]
    
    print("SIMPLE SPACING FIXER TEST")
    print("=" * 80)
    
    fixer = SmartSpacingFixer()
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        fixed = fixer.fix_spacing(input_text)
        
        print(f"\nExample {i}:")
        print(f"Input:    {input_text}")
        print(f"Fixed:    {fixed}")
        print(f"Expected: {expected}")
        
        # Calculate word accuracy
        fixed_words = fixed.lower().split()
        expected_words = expected.lower().split()
        matching = sum(1 for f, e in zip(fixed_words, expected_words) if f == e)
        accuracy = matching / max(len(fixed_words), len(expected_words))
        print(f"Accuracy: {accuracy:.1%}")
    
    # Test on longer text
    print("\n" + "=" * 80)
    print("LONGER TEXT EXAMPLE")
    print("=" * 80)
    
    long_text = """HIGHLIGHTS OF PRESCRIBING INFORMATIONThesehighlightsdonot includeall theinformationneededtouseFlublok®safelyand effectively.See full prescribing information for Flublok.Flublok (Influenza Vaccine)Injection for Intramuscular Use2024-2025 FormulaInitial U.S.Approval:2013"""
    
    print("\nOriginal:")
    print(long_text)
    
    print("\nFixed:")
    fixed = fix_pharmaceutical_text_spacing(long_text)
    print(fixed)
    
    # Test specific patterns
    print("\n" + "=" * 80)
    print("SPECIFIC PATTERN TESTS")
    print("=" * 80)
    
    patterns = [
        "0.5mL",
        "18years",
        "2024-2025Formula",
        "U.S.Approval",
        "safelyand",
        "donot",
        "neededto",
        "includeall",
        "(e.g.,anaphylaxis)",
    ]
    
    for pattern in patterns:
        fixed = fix_pharmaceutical_text_spacing(pattern)
        print(f"{pattern:20} -> {fixed}")


def test_with_pymupdf():
    """Test with real PyMuPDF extraction."""
    print("\n" + "=" * 80)
    print("REAL PYMUPDF EXTRACTION TEST")
    print("=" * 80)
    
    import json
    
    # Load the comparison results
    if Path('ocr_comparison_results.json').exists():
        with open('ocr_comparison_results.json', 'r') as f:
            results = json.load(f)
        
        # Test on first block
        pymupdf_text = results[0]['pymupdf']['text']
        
        print("\nOriginal PyMuPDF extraction:")
        print(pymupdf_text[:200] + "...")
        
        print("\nWith spacing fix:")
        fixed = fix_pharmaceutical_text_spacing(pymupdf_text)
        print(fixed[:200] + "...")
        
        # Compare with Tesseract result
        tesseract_text = results[0]['tesseract']['text']
        print("\nTesseract result (for comparison):")
        print(tesseract_text[:200] + "...")
        
        # Word accuracy
        fixed_words = fixed.lower().split()
        tesseract_words = tesseract_text.lower().split()
        matching = sum(1 for f, t in zip(fixed_words, tesseract_words) if f == t)
        accuracy = matching / max(len(fixed_words), len(tesseract_words))
        print(f"\nWord accuracy vs Tesseract: {accuracy:.1%}")


if __name__ == "__main__":
    test_spacing_fixes()
    test_with_pymupdf()