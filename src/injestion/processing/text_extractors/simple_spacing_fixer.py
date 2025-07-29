"""Simple spacing fixer without external dependencies."""

import re
from typing import List, Set, Tuple


class SimpleSpacingFixer:
    """Fix missing spaces in text using pattern matching."""
    
    def __init__(self):
        """Initialize with common word lists."""
        # Common English words for splitting
        self.common_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
            'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
            'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
            'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
            'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
            'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
            'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
            'give', 'day', 'most', 'us', 'is', 'are', 'been', 'has', 'had', 'were',
            'was', 'been', 'being', 'have', 'has', 'having', 'do', 'does', 'did',
            'done', 'doing', 'will', 'would', 'shall', 'should', 'may', 'might',
            'must', 'can', 'could', 'need', 'needed', 'information', 'include', 'all'
        }
        
        # Medical/pharmaceutical terms
        self.medical_terms = {
            'vaccine', 'influenza', 'immunization', 'intramuscular', 'injection',
            'contraindications', 'anaphylaxis', 'prescribing', 'dosage', 'dose',
            'administration', 'approval', 'formula', 'allergic', 'reaction',
            'highlights', 'information', 'flublok', 'indicated', 'prevention',
            'disease', 'caused', 'virus', 'approved', 'persons', 'years', 'age',
            'older', 'safely', 'effectively', 'severe', 'history', 'component',
            'administer', 'anyone', 'forms', 'strengths', 'usage', 'initial'
        }
        
        # Combine all words
        self.all_words = self.common_words | self.medical_terms
        
        # Add variations (uppercase, capitalized)
        word_variations = set()
        for word in self.all_words:
            word_variations.add(word.lower())
            word_variations.add(word.upper())
            word_variations.add(word.capitalize())
        self.all_words = word_variations
    
    def fix_spacing(self, text: str) -> str:
        """Fix spacing issues in text."""
        # Apply multiple fixing strategies
        text = self._fix_punctuation_spacing(text)
        text = self._fix_camel_case(text)
        text = self._fix_common_patterns(text)
        text = self._fix_concatenated_words(text)
        text = self._fix_number_spacing(text)
        
        # Clean up extra spaces
        text = ' '.join(text.split())
        return text
    
    def _fix_punctuation_spacing(self, text: str) -> str:
        """Fix spacing around punctuation."""
        # Add space after punctuation if followed by letter
        text = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)
        
        # Add space after closing parenthesis/bracket
        text = re.sub(r'([\)\]])([A-Za-z])', r'\1 \2', text)
        
        # Add space before opening parenthesis/bracket if preceded by letter
        text = re.sub(r'([A-Za-z])([\(\[])', r'\1 \2', text)
        
        # Fix multiple punctuation (e.g., "————————")
        text = re.sub(r'([—\-_]){3,}', r' \1\1\1 ', text)
        
        return text
    
    def _fix_camel_case(self, text: str) -> str:
        """Split camelCase words."""
        # Add space before uppercase letter that follows lowercase
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Handle acronyms (e.g., "USAToday" -> "USA Today")
        text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
        
        return text
    
    def _fix_common_patterns(self, text: str) -> str:
        """Fix common concatenation patterns."""
        # Common word combinations that should be split
        patterns = [
            # Articles and prepositions
            (r'(\w)(the)([A-Z])', r'\1 \2 \3'),
            (r'(\w)(and)([A-Z])', r'\1 \2 \3'),
            (r'(\w)(of)([A-Z])', r'\1 \2 \3'),
            (r'(\w)(to)([A-Z])', r'\1 \2 \3'),
            (r'(\w)(for)([A-Z])', r'\1 \2 \3'),
            (r'(\w)(in)([A-Z])', r'\1 \2 \3'),
            (r'(\w)(is)([A-Z])', r'\1 \2 \3'),
            
            # Common phrases
            (r'donot', 'do not'),
            (r'cannot', 'can not'),
            (r'willnot', 'will not'),
            (r'shouldnot', 'should not'),
            (r'doesnot', 'does not'),
            
            # Medical specific
            (r'theinformation', 'the information'),
            (r'neededto', 'needed to'),
            (r'touse', 'to use'),
            (r'tothe', 'to the'),
            (r'ofthe', 'of the'),
            (r'forthe', 'for the'),
            (r'andthe', 'and the'),
            (r'inthe', 'in the'),
            (r'includeall', 'include all'),
            (r'safelyand', 'safely and'),
            
            # Fix specific patterns
            (r'([a-z])(use|Use)([A-Z0-9])', r'\1 \2 \3'),
            (r'([a-z])(and|And)([a-z])', r'\1 \2 \3'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _fix_concatenated_words(self, text: str) -> str:
        """Split concatenated words using word list."""
        words = text.split()
        result = []
        
        for word in words:
            # Skip short words or words that are likely correct
            if len(word) <= 5 or word.lower() in self.all_words:
                result.append(word)
                continue
            
            # Try to split the word
            split_word = self._try_split_word(word)
            if split_word != word:
                result.append(split_word)
            else:
                result.append(word)
        
        return ' '.join(result)
    
    def _try_split_word(self, word: str) -> str:
        """Try to split a word into known components."""
        # Don't split years or codes
        if re.match(r'^\d{4}$', word) or re.match(r'^[A-Z]\d+[A-Z]?\d*$', word):
            return word
        
        word_lower = word.lower()
        best_split = None
        best_score = 0
        
        # Try all possible split points
        for i in range(3, len(word) - 2):  # Minimum word length of 3
            left = word_lower[:i]
            right = word_lower[i:]
            
            # Check if both parts are known words
            left_valid = left in self.all_words
            right_valid = right in self.all_words
            
            if left_valid and right_valid:
                # Score based on word lengths (prefer balanced splits)
                score = min(len(left), len(right))
                if score > best_score:
                    best_score = score
                    best_split = i
        
        if best_split:
            # Preserve original casing
            return word[:best_split] + ' ' + word[best_split:]
        
        # Try known prefixes/suffixes
        for prefix in ['pre', 'post', 'non', 'anti', 'sub', 'super']:
            if word_lower.startswith(prefix) and len(word) > len(prefix) + 3:
                rest = word[len(prefix):]
                if rest.lower() in self.all_words:
                    return word[:len(prefix)] + ' ' + rest
        
        return word
    
    def _fix_number_spacing(self, text: str) -> str:
        """Fix spacing around numbers."""
        # Add space between number and text (but not within years/codes)
        text = re.sub(r'(\d)([A-Za-z])', lambda m: m.group(1) + ' ' + m.group(2)
                     if not re.match(r'^\d{4}$', m.group(0)) else m.group(0), text)
        
        # Add space between text and number for specific patterns
        text = re.sub(r'([A-Za-z])(\d)', lambda m: m.group(1) + ' ' + m.group(2)
                     if m.group(1).lower() in ['use', 'formula', 'approval'] 
                     else m.group(0), text)
        
        # Fix patterns like "(0.5mL)" -> "(0.5 mL)"
        text = re.sub(r'(\d+\.?\d*)(mL|mg|mcg|IU)', r'\1 \2', text)
        
        return text


def fix_text_spacing(text: str) -> str:
    """Convenience function to fix spacing in text."""
    fixer = SimpleSpacingFixer()
    return fixer.fix_spacing(text)