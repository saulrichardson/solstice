#!/usr/bin/env python3
"""Test the spacing fixer on real extracted text."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.injestion.processing.text_extractors.spacing_fixer import SpacingFixer, SmartSpacingFixer, fix_extracted_text


def test_spacing_fixes():
    """Test spacing fixes on real examples."""
    
    # Real examples from the PDF
    test_cases = [
        "Thesehighlightsdonot includeall theinformationneededtouseFlublok®safely",
        "HIGHLIGHTS OF PRESCRIBING INFORMATIONThesehighlightsdonot",
        "Flublok (Influenza Vaccine)Injection for Intramuscular Use2024-2025 FormulaInitial U.S. Approval:2013",
        "DOSAGE AND ADMINISTRATION——————————For intramuscular use(0.5 mL).(2)",
        "• Do not administer Flublokto anyone with ahistory of severe",
        "———————————INDICATIONS AND USAGE———————————Flublok is avaccine indicated",
    ]
    
    print("SPACING FIXER COMPARISON")
    print("=" * 80)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nExample {i}:")
        print(f"Original:    {text}")
        
        # Test basic fixer (no dictionary)
        basic_fixer = SpacingFixer(use_dictionary=False)
        basic_fixed = basic_fixer.fix_spacing(text)
        print(f"Basic fix:   {basic_fixed}")
        
        # Test smart fixer
        smart_fixer = SmartSpacingFixer()
        smart_fixed = smart_fixer.fix_spacing_with_context(text)
        print(f"Smart fix:   {smart_fixed}")
        
        # Test convenience function
        aggressive_fixed = fix_extracted_text(text, aggressive=True)
        print(f"Aggressive:  {aggressive_fixed}")
    
    # Test on longer text
    print("\n" + "=" * 80)
    print("LONGER TEXT EXAMPLE")
    print("=" * 80)
    
    long_text = """HIGHLIGHTS OF PRESCRIBING INFORMATIONThesehighlightsdonot includeall theinformationneededtouseFlublok®safelyand effectively. See full prescribing information for Flublok.Flublok (Influenza Vaccine)Injection for Intramuscular Use2024-2025 FormulaInitial U.S. Approval:2013"""
    
    print("\nOriginal:")
    print(long_text[:100] + "...")
    
    print("\nBasic fix:")
    basic_fixed = fix_extracted_text(long_text, aggressive=False)
    print(basic_fixed[:100] + "...")
    
    print("\nAggressive fix:")
    aggressive_fixed = fix_extracted_text(long_text, aggressive=True)
    print(aggressive_fixed[:100] + "...")
    
    # Compare with expected
    expected = "HIGHLIGHTS OF PRESCRIBING INFORMATION These highlights do not include all the information needed to use Flublok® safely and effectively. See full prescribing information for Flublok. Flublok (Influenza Vaccine) Injection for Intramuscular Use 2024-2025 Formula Initial U.S. Approval: 2013"
    
    print("\nExpected:")
    print(expected[:100] + "...")
    
    # Calculate accuracy
    def word_accuracy(text1, text2):
        words1 = text1.lower().split()
        words2 = text2.lower().split()
        correct = sum(1 for w1, w2 in zip(words1, words2) if w1 == w2)
        return correct / max(len(words1), len(words2))
    
    print(f"\nWord accuracy:")
    print(f"  Basic fix:      {word_accuracy(basic_fixed, expected):.1%}")
    print(f"  Aggressive fix: {word_accuracy(aggressive_fixed, expected):.1%}")


def test_pymupdf_with_fixer():
    """Test PyMuPDF extraction with spacing fixer."""
    print("\n" + "=" * 80)
    print("PYMUPDF + SPACING FIXER")
    print("=" * 80)
    
    import fitz
    
    pdf_path = Path("data/clinical_files/FlublokPI.pdf")
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    
    # Get first text block
    blocks = page.get_text("dict")
    for block in blocks.get("blocks", []):
        if block.get("type") == 0:  # Text block
            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span.get("text", "")
            
            if len(text) > 50:
                print(f"\nOriginal PyMuPDF extraction:")
                print(f"{text[:150]}...")
                
                print(f"\nWith basic spacing fix:")
                fixed = fix_extracted_text(text, aggressive=False)
                print(f"{fixed[:150]}...")
                
                print(f"\nWith aggressive spacing fix:")
                fixed_aggressive = fix_extracted_text(text, aggressive=True)
                print(f"{fixed_aggressive[:150]}...")
                
                break
    
    doc.close()


if __name__ == "__main__":
    # First install required packages if needed
    try:
        import nltk
        import enchant
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nltk", "pyenchant"])
    
    test_spacing_fixes()
    test_pymupdf_with_fixer()