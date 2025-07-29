#!/usr/bin/env python3
"""Analyze text extraction quality between Tesseract and PyMuPDF."""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def normalize_text(text):
    """Normalize text for fair comparison."""
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove special characters for word comparison
    text = re.sub(r'[—_\-]+', '-', text)
    return text.strip()


def word_accuracy(text1, text2):
    """Calculate word-level accuracy."""
    words1 = normalize_text(text1).lower().split()
    words2 = normalize_text(text2).lower().split()
    
    # Use sequence matcher for word-level comparison
    matcher = SequenceMatcher(None, words1, words2)
    return matcher.ratio()


def analyze_results():
    """Analyze the OCR comparison results."""
    
    # Load results
    with open('ocr_comparison_results.json', 'r') as f:
        results = json.load(f)
    
    print("TEXT EXTRACTION QUALITY ANALYSIS")
    print("=" * 60)
    print()
    
    # Expected text for each block (manually corrected)
    expected_texts = [
        "HIGHLIGHTS OF PRESCRIBING INFORMATION These highlights do not include all the information needed to use Flublok® safely and effectively. See full prescribing information for Flublok. Flublok (Influenza Vaccine) Injection for Intramuscular Use 2024-2025 Formula Initial U.S. Approval: 2013",
        "INDICATIONS AND USAGE Flublok is a vaccine indicated for active immunization for the prevention of disease caused by influenza A virus subtypes and influenza type B virus contained in the vaccine. Flublok is approved for use in persons 18 years of age and older. (1)",
        "DOSAGE AND ADMINISTRATION For intramuscular use (0.5 mL). (2)",
        "DOSAGE FORMS AND STRENGTHS Flublok is an injection, a single dose is 0.5mL. (3)",
        "CONTRAINDICATIONS • Do not administer Flublok to anyone with a history of severe allergic reactions (e.g., anaphylaxis) to any component of the vaccine. (4, 6.2, 11)"
    ]
    
    for i, (result, expected) in enumerate(zip(results, expected_texts)):
        print(f"BLOCK {i+1}")
        print("-" * 60)
        
        tesseract_text = result['tesseract']['text']
        pymupdf_text = result['pymupdf']['text']
        
        # Calculate word accuracy against expected text
        tesseract_word_acc = word_accuracy(tesseract_text, expected)
        pymupdf_word_acc = word_accuracy(pymupdf_text, expected)
        
        print(f"Expected text ({len(expected)} chars):")
        print(f"  {expected[:100]}...")
        print()
        
        print(f"Tesseract ({len(tesseract_text)} chars, {tesseract_word_acc:.2%} word accuracy):")
        print(f"  {normalize_text(tesseract_text)[:100]}...")
        print()
        
        print(f"PyMuPDF ({len(pymupdf_text)} chars, {pymupdf_word_acc:.2%} word accuracy):")
        print(f"  {normalize_text(pymupdf_text)[:100]}...")
        print()
        
        # Identify specific issues
        print("Issues:")
        
        # Check for spacing issues in PyMuPDF
        if "donot" in pymupdf_text.lower() or "thesehighlights" in pymupdf_text.lower():
            print("  - PyMuPDF: Missing spaces between words")
        
        # Check for OCR errors in Tesseract
        tesseract_norm = normalize_text(tesseract_text).lower()
        expected_norm = normalize_text(expected).lower()
        
        if "—" in tesseract_text and "—" not in expected:
            print("  - Tesseract: Incorrect dash characters")
        
        # Compare key terms
        key_terms = ["flublok", "vaccine", "influenza", "2024-2025"]
        for term in key_terms:
            if term in expected_norm:
                if term not in tesseract_norm:
                    print(f"  - Tesseract: Missing key term '{term}'")
                if term not in normalize_text(pymupdf_text).lower():
                    print(f"  - PyMuPDF: Missing key term '{term}'")
        
        print()
    
    # Overall summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_tesseract_acc = sum(word_accuracy(r['tesseract']['text'], exp) 
                             for r, exp in zip(results, expected_texts)) / len(results)
    total_pymupdf_acc = sum(word_accuracy(r['pymupdf']['text'], exp) 
                           for r, exp in zip(results, expected_texts)) / len(results)
    
    print(f"\nAverage Word-Level Accuracy:")
    print(f"  Tesseract: {total_tesseract_acc:.1%}")
    print(f"  PyMuPDF:   {total_pymupdf_acc:.1%}")
    
    print(f"\nAverage Extraction Time:")
    print(f"  Tesseract: {sum(r['tesseract']['time'] for r in results) / len(results):.3f}s")
    print(f"  PyMuPDF:   {sum(r['pymupdf']['time'] for r in results) / len(results):.3f}s")
    
    print(f"\nConclusion:")
    if total_tesseract_acc > total_pymupdf_acc:
        print("  Tesseract provides better text extraction quality (properly spaced words)")
        print("  but is significantly slower than PyMuPDF.")
    else:
        print("  PyMuPDF provides better raw extraction but has spacing issues.")
        print("  Tesseract attempts to fix spacing but sometimes introduces errors.")
    
    # Show specific examples
    print("\n" + "=" * 60)
    print("SPECIFIC EXAMPLE - Block 1")
    print("=" * 60)
    
    block1 = results[0]
    print("\nKey phrase comparison:")
    print("  Expected:  'These highlights do not include'")
    print(f"  Tesseract: '{normalize_text(block1['tesseract']['text'])[38:70]}'")
    print(f"  PyMuPDF:   '{normalize_text(block1['pymupdf']['text'])[38:70]}'")
    
    print("\nSpacing issue example:")
    print("  Original PDF text: 'Thesehighlightsdonot'")
    print("  Tesseract fixed:   'These highlights do not'")
    print("  PyMuPDF preserved: 'Thesehighlightsdonot'")


if __name__ == "__main__":
    if not Path('ocr_comparison_results.json').exists():
        print("Run compare_ocr_methods.py first to generate results.")
    else:
        analyze_results()