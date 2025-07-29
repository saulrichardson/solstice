"""Production-ready spacing fixer using WordNinja."""

import re
from typing import List, Optional


class WordNinjaSpacingFixer:
    """Fix spacing issues using WordNinja for word segmentation."""
    
    def __init__(self):
        """Initialize the fixer."""
        try:
            import wordninja
            self.wordninja = wordninja
            self.available = True
        except ImportError:
            self.available = False
            print("WordNinja not installed. Install with: pip install wordninja")
    
    def fix_spacing(self, text: str) -> str:
        """
        Fix spacing issues in text extracted by PyMuPDF.
        
        Args:
            text: Text with potential spacing issues
            
        Returns:
            Text with fixed spacing
        """
        if not self.available:
            return text
        
        # Step 1: Fix punctuation spacing (always safe)
        text = self._fix_punctuation_spacing(text)
        
        # Step 2: Process each word
        words = text.split()
        result = []
        
        for word in words:
            fixed_word = self._process_word(word)
            if isinstance(fixed_word, list):
                result.extend(fixed_word)
            else:
                result.append(fixed_word)
        
        # Step 3: Join and clean up
        text = ' '.join(result)
        
        # Step 4: Fix specific patterns
        text = self._fix_specific_patterns(text)
        
        return text
    
    def _fix_punctuation_spacing(self, text: str) -> str:
        """Fix spacing around punctuation."""
        # Add space after sentence-ending punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        # Add space after comma, semicolon, colon
        text = re.sub(r'([,:;])([A-Za-z])', r'\1 \2', text)
        
        # Fix parentheses
        text = re.sub(r'\)([A-Za-z])', r') \1', text)
        text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
        
        # Fix quotes
        text = re.sub(r'"([A-Za-z])', r'" \1', text)
        text = re.sub(r'([A-Za-z])"', r'\1 "', text)
        
        return text
    
    def _process_word(self, word: str) -> any:
        """Process a single word, splitting if necessary."""
        # Don't process short words
        if len(word) <= 4:
            return word
        
        # Don't process numbers or codes
        if word.isdigit() or re.match(r'^[A-Z0-9\-]+$', word):
            return word
        
        # Don't process words with special characters (except common ones)
        if re.search(r'[^\w\-\'.®™]', word):
            return word
        
        # Check for specific patterns that shouldn't be split
        if self._should_preserve(word):
            return word
        
        # Remove trailing punctuation temporarily
        trailing_punct = ''
        while word and word[-1] in '.,;:!?"\'':
            trailing_punct = word[-1] + trailing_punct
            word = word[:-1]
        
        # Use WordNinja to split
        lower_word = word.lower()
        split_words = self.wordninja.split(lower_word)
        
        # Check if split makes sense
        if not self._is_good_split(word, split_words):
            return word + trailing_punct
        
        # Restore capitalization
        result = self._restore_capitalization(word, split_words)
        
        # Add back trailing punctuation to last word
        if trailing_punct and result:
            result[-1] += trailing_punct
        
        return result
    
    def _should_preserve(self, word: str) -> bool:
        """Check if word should be preserved as-is."""
        # Medical/pharmaceutical terms that might be split incorrectly
        preserve_words = {
            'flublok', 'influenza', 'vaccine', 'intramuscular', 'immunization',
            'contraindications', 'anaphylaxis', 'administration', 'prescribing'
        }
        
        # Check if word (lowercase) is in preserve list
        if word.lower() in preserve_words:
            return True
        
        # Check for mixed case in middle (likely correct)
        if any(c.isupper() for c in word[1:-1]) and any(c.islower() for c in word):
            return True
        
        # Check for version numbers, codes
        if re.match(r'^\w+\d+\.\d+', word):  # e.g., "v2.0.1"
            return True
        
        return False
    
    def _is_good_split(self, original: str, split_words: List[str]) -> bool:
        """Check if the split makes sense."""
        # Don't split into too many tiny pieces
        if len(split_words) > len(original) / 3:
            return False
        
        # Don't split if any resulting word is too short (except common ones)
        common_short = {'a', 'i', 'to', 'of', 'in', 'is', 'it', 'on', 'at', 'by', 'or', 'an'}
        for word in split_words:
            if len(word) == 1 and word not in {'a', 'i'}:
                return False
            if len(word) == 2 and word not in common_short:
                return False
        
        return True
    
    def _restore_capitalization(self, original: str, split_words: List[str]) -> List[str]:
        """Restore the original capitalization pattern."""
        result = split_words.copy()
        
        # If original was all caps and long enough, make result all caps
        if original.isupper() and len(original) > 6:
            # Don't uppercase short common words
            short_words = {'of', 'and', 'the', 'to', 'in', 'a', 'an', 'is', 'it', 'on', 'at', 'by', 'or'}
            result = [w.upper() if w not in short_words else w for w in result]
        
        # If original started with capital, capitalize first word
        elif original[0].isupper():
            result[0] = result[0].capitalize()
        
        # Handle title case (each word capitalized)
        elif sum(1 for c in original if c.isupper()) > 1:
            # Try to maintain title case for major words
            result = [w.capitalize() if len(w) > 3 else w for w in result]
        
        return result
    
    def _fix_specific_patterns(self, text: str) -> str:
        """Fix specific patterns that WordNinja might miss."""
        # Fix units (WordNinja splits "0.5mL" incorrectly)
        text = re.sub(r'(\d+\.?\d*)\s*m\s*l\b', r'\1 mL', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+\.?\d*)\s*m\s*g\b', r'\1 mg', text, flags=re.IGNORECASE)
        text = re.sub(r'(\d+\.?\d*)\s*mc\s*g\b', r'\1 mcg', text, flags=re.IGNORECASE)
        
        # Fix "U. S." -> "U.S."
        text = re.sub(r'U\.\s*S\.', 'U.S.', text)
        
        # Fix years that got split
        text = re.sub(r':\s*(\d)\s*(\d)\s*(\d)\s*(\d)\b', r': \1\2\3\4', text)
        
        # Fix common word pairs that might be over-split
        text = re.sub(r'\bdo\s+not\b', 'do not', text, flags=re.IGNORECASE)
        text = re.sub(r'\bcan\s+not\b', 'cannot', text, flags=re.IGNORECASE)
        
        return text


def fix_pymupdf_text_spacing(text: str) -> str:
    """
    Convenience function to fix spacing in PyMuPDF extracted text.
    
    Args:
        text: Text extracted by PyMuPDF with potential spacing issues
        
    Returns:
        Text with fixed spacing
        
    Example:
        >>> fix_pymupdf_text_spacing("Thesehighlightsdonot includeall")
        "These highlights do not include all"
    """
    fixer = WordNinjaSpacingFixer()
    return fixer.fix_spacing(text)