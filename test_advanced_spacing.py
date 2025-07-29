#!/usr/bin/env python3
"""Test advanced spacing fixers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_wordninja():
    """Test WordNinja approach - the most practical solution."""
    try:
        import wordninja
    except ImportError:
        print("Installing wordninja...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wordninja"])
        import wordninja
    
    print("WORDNINJA SPACING FIXER")
    print("=" * 80)
    
    test_cases = [
        "Thesehighlightsdonot",
        "includeall",
        "theinformationneededtouseFlublok",
        "safelyandeffectively",
        "HIGHLIGHTSOFPRESCRIBINGINFORMATION",
        "18yearsofageandolder",
        "0.5mL",
        "U.S.Approval:2013",
    ]
    
    for text in test_cases:
        # WordNinja works on lowercase, so we need to preserve case
        original_case = text
        
        # Split the text
        words = wordninja.split(text.lower())
        
        # Restore case intelligently
        if text[0].isupper():
            words[0] = words[0].capitalize()
        
        # Handle all caps
        if text.isupper():
            words = [w.upper() for w in words]
        
        result = ' '.join(words)
        
        print(f"\nOriginal: {text}")
        print(f"Fixed:    {result}")
        print(f"Words:    {words}")


def test_advanced_fixer():
    """Test the advanced hybrid fixer."""
    from src.injestion.processing.text_extractors.advanced_spacing_fixer import HybridSpacingFixer
    
    print("\n" + "=" * 80)
    print("HYBRID SPACING FIXER")
    print("=" * 80)
    
    fixer = HybridSpacingFixer()
    
    # Real examples from the PDF
    test_cases = [
        "Thesehighlightsdonot includeall theinformationneededtouseFlublok®safely",
        "HIGHLIGHTS OF PRESCRIBING INFORMATIONThesehighlightsdonot",
        "Flublok (Influenza Vaccine)Injection for Intramuscular Use2024-2025 FormulaInitial",
        "• Do not administer Flublokto anyone with ahistory of severe",
    ]
    
    for text in test_cases:
        fixed = fixer.fix_spacing(text)
        print(f"\nOriginal: {text}")
        print(f"Fixed:    {fixed}")


def test_practical_solution():
    """Test a practical solution using wordninja."""
    print("\n" + "=" * 80)
    print("PRACTICAL SOLUTION FOR PYMUPDF")
    print("=" * 80)
    
    import wordninja
    
    def fix_pymupdf_spacing(text: str) -> str:
        """Practical spacing fixer using WordNinja."""
        import re
        
        # Step 1: Fix punctuation spacing
        text = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)
        text = re.sub(r'\)([A-Za-z])', r') \1', text)
        text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
        
        # Step 2: Split words
        words = text.split()
        result = []
        
        for word in words:
            # Skip if too short or looks like a year/code
            if len(word) <= 4 or re.match(r'^\d{4}$', word):
                result.append(word)
                continue
            
            # Skip if it has mixed case in the middle (likely correct)
            if any(c.isupper() for c in word[1:-1]) and any(c.islower() for c in word):
                result.append(word)
                continue
            
            # Try to split concatenated words
            lower_word = word.lower()
            split_words = wordninja.split(lower_word)
            
            # Only accept split if it makes sense
            if len(split_words) > 1 and all(len(w) >= 2 for w in split_words):
                # Restore capitalization
                if word[0].isupper():
                    split_words[0] = split_words[0].capitalize()
                
                # Handle special cases
                if word.isupper() and len(word) > 6:
                    # Don't uppercase short words like "of", "and"
                    split_words = [w.upper() if len(w) > 3 else w for w in split_words]
                
                result.extend(split_words)
            else:
                result.append(word)
        
        # Step 3: Fix specific patterns
        text = ' '.join(result)
        
        # Fix units
        text = re.sub(r'(\d+\.?\d*)(ml|mg|mcg)\b', r'\1 \2', text, flags=re.IGNORECASE)
        
        # Fix years
        text = re.sub(r'(\w+)(\d{4})', lambda m: m.group(1) + ' ' + m.group(2) 
                     if m.group(1).lower() in ['use', 'approval'] else m.group(0), text)
        
        return text
    
    # Test with real examples
    import json
    if Path('ocr_comparison_results.json').exists():
        with open('ocr_comparison_results.json', 'r') as f:
            results = json.load(f)
        
        pymupdf_text = results[0]['pymupdf']['text']
        tesseract_text = results[0]['tesseract']['text']
        
        fixed = fix_pymupdf_spacing(pymupdf_text)
        
        print("\nOriginal PyMuPDF:")
        print(pymupdf_text[:200] + "...")
        
        print("\nFixed with WordNinja:")
        print(fixed[:200] + "...")
        
        print("\nTesseract (reference):")
        print(tesseract_text[:200] + "...")
        
        # Calculate word accuracy
        def word_accuracy(text1, text2):
            words1 = text1.lower().split()
            words2 = text2.lower().split()
            matches = sum(1 for w1, w2 in zip(words1, words2) if w1 == w2)
            return matches / max(len(words1), len(words2))
        
        print(f"\nWord accuracy vs Tesseract: {word_accuracy(fixed, tesseract_text):.1%}")


def explain_strategies():
    """Explain common strategies for fixing spacing."""
    print("\n" + "=" * 80)
    print("COMMON STRATEGIES FOR FIXING SPACING")
    print("=" * 80)
    
    print("""
1. **Dictionary-based Word Segmentation** (WordNinja, SymSpell)
   - Uses word frequency data (Google n-grams, Wikipedia, etc.)
   - Finds most likely word boundaries using dynamic programming
   - Best for: "thesehighlights" → "these highlights"
   
2. **Statistical Language Models**
   - N-gram models to predict word boundaries
   - Character-level LSTMs trained on correctly spaced text
   - Transformer models (BERT) for context-aware splitting
   
3. **Rule-based Approaches**
   - Regex patterns for common concatenations
   - Linguistic rules (e.g., consonant clusters at word boundaries)
   - Domain-specific dictionaries
   
4. **Hybrid Approaches**
   - Combine dictionary lookup with ML models
   - Use rules as pre/post-processing steps
   - Ensemble multiple methods
   
5. **Grammar Checkers** (LanguageTool, Grammarly API)
   - Detect and fix spacing as grammar errors
   - Context-aware corrections
   - Slower but more accurate

**Recommended Approach:**
- Use WordNinja for general text (fast, accurate, no training needed)
- Add domain-specific dictionary for medical terms
- Apply simple rules for punctuation and numbers
- Fall back to OCR (Tesseract) for severely corrupted text
""")


if __name__ == "__main__":
    test_wordninja()
    test_advanced_fixer()
    test_practical_solution()
    explain_strategies()