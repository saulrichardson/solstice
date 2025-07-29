"""Final production-ready spacing fixer using WordNinja."""

import re
from typing import List, Set

import wordninja


class FinalSpacingFixer:
    """Production-ready spacing fixer for PyMuPDF text."""
    
    def __init__(self):
        
        # Words that should never be split
        self.preserve_words = {
            'flublok', 'covid', 'mrna', 'sars', 'igg', 
            'influenza', 'vaccine', 'intramuscular'
        }
        
        # Common short words that are valid
        self.valid_short_words = {
            'a', 'i', 'an', 'as', 'at', 'be', 'by', 'do', 'go', 'he', 
            'if', 'in', 'is', 'it', 'me', 'my', 'no', 'of', 'on', 'or',
            'so', 'to', 'up', 'us', 'we', 'the', 'and', 'for', 'not',
            'are', 'but', 'can', 'did', 'get', 'had', 'has', 'her', 'him',
            'his', 'how', 'its', 'may', 'new', 'now', 'old', 'one', 'our',
            'out', 'see', 'she', 'two', 'use', 'was', 'way', 'who', 'you',
            'all', 'any', 'few', 'own', 'too'
        }
    
    def fix_spacing(self, text: str) -> str:
        """Fix spacing in text."""
        # Step 1: Fix punctuation
        text = self._fix_punctuation(text)
        
        # Step 2: Process words
        words = text.split()
        result = []
        
        for word in words:
            # Extract and store punctuation
            word_clean, prefix, suffix = self._extract_punctuation(word)
            
            # Process the clean word
            if self._should_split(word_clean):
                split_words = self._split_word(word_clean)
                # Add prefix to first word, suffix to last
                if split_words:
                    split_words[0] = prefix + split_words[0]
                    split_words[-1] = split_words[-1] + suffix
                    result.extend(split_words)
            else:
                result.append(prefix + word_clean + suffix)
        
        # Step 3: Join and fix specific patterns
        text = ' '.join(result)
        text = self._fix_specific_patterns(text)
        
        return text
    
    def _fix_punctuation(self, text: str) -> str:
        """Fix spacing around punctuation."""
        # Add space after sentence-ending punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        # Add space after comma, colon, semicolon
        text = re.sub(r'([,:;])([A-Za-z])', r'\1 \2', text)
        # Fix parentheses
        text = re.sub(r'\)([A-Za-z])', r') \1', text)
        text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
        return text
    
    def _extract_punctuation(self, word: str) -> tuple:
        """Extract leading and trailing punctuation."""
        prefix = ''
        suffix = ''
        
        # Extract leading punctuation
        while word and not (word[0].isalnum() or word[0] in '®™'):
            prefix += word[0]
            word = word[1:]
        
        # Extract trailing punctuation (but keep ® and ™ with the word)
        while word and word[-1] in '.,;:!?\'"':
            suffix = word[-1] + suffix
            word = word[:-1]
        
        return word, prefix, suffix
    
    def _should_split(self, word: str) -> bool:
        """Determine if a word should be split."""
        # Don't split short words
        if len(word) <= 5:
            return False
        
        # Don't split numbers or codes
        if word.isdigit() or re.match(r'^[A-Z0-9\-]+$', word):
            return False
        
        # Don't split if it contains special characters that might break
        if '®' in word or '™' in word:
            # Remove the symbol and check the rest
            word = word.replace('®', '').replace('™', '')
        
        # Don't split preserved words
        if word.lower() in self.preserve_words:
            return False
        
        # For very long words (likely concatenated), always try to split
        if len(word) > 20:
            # Skip the mixed case check for long words
            pass
        else:
            # Don't split if it has mixed case in the middle (likely correct)
            # e.g., "JavaScript", "iPhone"
            inner = word[1:-1] if len(word) > 2 else ''
            if inner and any(c.isupper() for c in inner) and any(c.islower() for c in inner):
                return False
        
        # Try splitting to see if we get multiple valid words
        test_split = wordninja.split(word.lower())
        if len(test_split) > 1:
            # It split into multiple words, probably needs splitting
            return True
        
        # Single word result - only split if it's very long
        return len(word) > 15
    
    def _split_word(self, word: str) -> List[str]:
        """Split a word using WordNinja."""
        # Handle special symbols
        has_symbol = '®' in word or '™' in word
        clean_word = word.replace('®', '').replace('™', '')
        
        # Get the split
        split_words = wordninja.split(clean_word.lower())
        
        # Validate the split
        if not self._validate_split(split_words):
            return [word]
        
        # If we had a symbol, add it back to the appropriate word
        if has_symbol and '®' in word:
            # Handle "flu blok" being split from "flublok"
            words_lower = [w.lower() for w in split_words]
            if 'flu' in words_lower and 'blok' in words_lower:
                flu_idx = words_lower.index('flu')
                blok_idx = words_lower.index('blok')
                if blok_idx == flu_idx + 1:  # They're adjacent
                    # Merge them back and add symbol
                    split_words[flu_idx] = 'Flublok®'
                    split_words.pop(blok_idx)
            elif 'flublok' in words_lower:
                idx = words_lower.index('flublok')
                split_words[idx] = split_words[idx] + '®'
        
        # Restore capitalization
        return self._restore_case(clean_word, split_words)
    
    def _validate_split(self, split_words: List[str]) -> bool:
        """Check if a split is valid."""
        # Don't accept too many tiny pieces (unless they're mostly valid words)
        if len(split_words) > 10:
            return False
        
        # Check each word
        for word in split_words:
            # Accept valid short words
            if word in self.valid_short_words:
                continue
            # Accept pure numeric tokens (e.g. "18") that are meaningful on
            # their own. Treating them as invalid causes the entire split to
            # be rejected which in turn prevents WordNinja from separating
            # strings like "18yearsandolder".
            if word.isdigit():
                continue
            # Reject single letters except 'a' and 'i'
            if len(word) == 1 and word not in ['a', 'i']:
                return False
            # Reject very short words unless they're known valid
            if len(word) == 2 and word not in self.valid_short_words:
                return False
        
        return True
    
    def _restore_case(self, original: str, split_words: List[str]) -> List[str]:
        """Restore the original case pattern."""
        result = split_words.copy()
        
        # All uppercase
        if original.isupper():
            # Keep short common words lowercase in uppercase text
            keep_lower = {'of', 'and', 'the', 'to', 'for', 'in', 'a', 'an'}
            result = [w.upper() if w not in keep_lower else w for w in result]
        
        # First letter capitalized
        elif original[0].isupper():
            result[0] = result[0].capitalize()
            
            # Check if it's title case (multiple capitals)
            cap_count = sum(1 for c in original if c.isupper())
            if cap_count > 1 and cap_count < len(original) / 2:
                # Probably title case, capitalize major words
                result = [w.capitalize() if len(w) > 3 else w for w in result]
        
        return result
    
    def _fix_specific_patterns(self, text: str) -> str:
        """Fix specific patterns that need attention."""
        # Fix units that might not have been caught
        text = re.sub(r'(\d+\.?\d*)mL', r'\1 mL', text)
        text = re.sub(r'(\d+\.?\d*)mg', r'\1 mg', text)
        text = re.sub(r'(\d+\.?\d*)mcg', r'\1 mcg', text)
        
        # Fix units that were split incorrectly
        text = re.sub(r'(\d+\.?\d*)\s+m\s+l\b', r'\1 mL', text)
        
        # Fix years
        text = re.sub(r'(\d+)years', r'\1 years', text)
        text = re.sub(r'(\d+)\s+years', r'\1 years', text)
        
        # Fix U.S.
        text = re.sub(r'U\.\s*S\.', 'U.S.', text)
        
        # Fix year ranges
        text = re.sub(r'(\d{4})\s+(\d{4})', r'\1-\2', text)
        
        # Fix specific drug names that might be split wrong
        text = re.sub(r'Flu\s+blok', 'Flublok', text, flags=re.IGNORECASE)
        
        # Fix common medical document patterns
        text = re.sub(r'(\d+\.?\d*)\s*mLdose', r'\1 mL dose', text)
        text = re.sub(r'mcgHA', 'mcg HA', text)
        text = re.sub(r'HAof', 'HA of', text)
        text = re.sub(r'Each(\d)', r'Each \1', text)
        text = re.sub(r'(\d+)of', r'\1 of', text)
        
        # Fix specific concatenations found in medical docs
        text = re.sub(r'isthe', 'is the', text)
        text = re.sub(r'oneor', 'one or', text)
        text = re.sub(r'forthe', 'for the', text)
        text = re.sub(r'fromthe', 'from the', text)
        text = re.sub(r'tothe', 'to the', text)
        text = re.sub(r'ofthe', 'of the', text)
        text = re.sub(r'inthe', 'in the', text)
        text = re.sub(r'andthe', 'and the', text)
        
        return text


def fix_pdf_text_spacing(text: str) -> str:
    """
    Fix spacing issues in PDF extracted text.
    
    This is the main entry point for fixing text extracted by PyMuPDF.
    
    Args:
        text: Text with potential spacing issues
        
    Returns:
        Text with improved spacing
        
    Example:
        >>> fix_pdf_text_spacing("Thesehighlightsdonot includeall")
        "These highlights do not include all"
    """
    if not WORDNINJA_AVAILABLE:
        print("WordNinja not available. Install with: pip install wordninja")
        return text
    
    fixer = FinalSpacingFixer()
    return fixer.fix_spacing(text)
