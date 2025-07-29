"""Fix spacing issues in extracted text."""

import re
from typing import List, Dict, Set
import nltk
from nltk.corpus import words
import enchant


class SpacingFixer:
    """Fix missing spaces in text using various strategies."""
    
    def __init__(self, use_dictionary: bool = True):
        """
        Initialize the spacing fixer.
        
        Args:
            use_dictionary: Whether to use dictionary-based splitting
        """
        self.use_dictionary = use_dictionary
        
        if use_dictionary:
            try:
                # Try to load NLTK words corpus
                self._word_set = set(words.words())
            except:
                # Download if not available
                nltk.download('words')
                self._word_set = set(words.words())
            
            # Add medical/pharma terms not in standard dictionary
            self._add_medical_terms()
            
            # Try to use enchant for better spell checking
            try:
                self._spell_checker = enchant.Dict("en_US")
            except:
                self._spell_checker = None
    
    def _add_medical_terms(self):
        """Add common medical/pharmaceutical terms."""
        medical_terms = {
            'flublok', 'vaccine', 'influenza', 'immunization', 'intramuscular',
            'contraindications', 'anaphylaxis', 'prescribing', 'dosage',
            'administration', 'approval', 'formula', 'injection', 'allergic'
        }
        self._word_set.update(medical_terms)
        self._word_set.update([term.upper() for term in medical_terms])
        self._word_set.update([term.capitalize() for term in medical_terms])
    
    def fix_spacing(self, text: str) -> str:
        """
        Fix spacing issues in text using multiple strategies.
        
        Args:
            text: Text with potential spacing issues
            
        Returns:
            Text with improved spacing
        """
        # Strategy 1: Fix common patterns
        text = self._fix_common_patterns(text)
        
        # Strategy 2: Fix camelCase splitting
        text = self._split_camel_case(text)
        
        # Strategy 3: Dictionary-based word splitting
        if self.use_dictionary:
            text = self._dictionary_split(text)
        
        # Strategy 4: Fix specific pharmaceutical patterns
        text = self._fix_pharma_patterns(text)
        
        # Clean up extra spaces
        text = ' '.join(text.split())
        
        return text
    
    def _fix_common_patterns(self, text: str) -> str:
        """Fix common spacing patterns."""
        patterns = [
            # Fix missing space after punctuation
            (r'([.!?])([A-Z])', r'\1 \2'),
            # Fix missing space after closing parenthesis
            (r'\)([A-Za-z])', r') \1'),
            # Fix missing space before opening parenthesis
            (r'([A-Za-z])\(', r'\1 ('),
            # Fix missing space after comma
            (r',([A-Za-z])', r', \1'),
            # Fix missing space after colon
            (r':([A-Za-z])', r': \1'),
            # Fix number followed by text
            (r'(\d)([A-Za-z])', r'\1 \2'),
            # Fix text followed by number (but not within words like "2024")
            (r'([A-Za-z])(\d)', lambda m: m.group(1) + ' ' + m.group(2) 
             if not self._is_likely_year_or_code(m.group(0)) else m.group(0)),
        ]
        
        for pattern, replacement in patterns:
            if callable(replacement):
                text = re.sub(pattern, replacement, text)
            else:
                text = re.sub(pattern, replacement, text)
        
        return text
    
    def _is_likely_year_or_code(self, text: str) -> bool:
        """Check if text is likely a year or product code."""
        # Years like 2024, codes like H1N1
        return bool(re.match(r'^[A-Z]\d[A-Z]\d$', text) or 
                   re.match(r'^(19|20)\d\d$', text))
    
    def _split_camel_case(self, text: str) -> str:
        """Split camelCase words."""
        # Insert space before uppercase letters that follow lowercase
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Handle acronyms followed by words (e.g., "USAToday" -> "USA Today")
        text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
        
        return text
    
    def _dictionary_split(self, text: str) -> str:
        """Split concatenated words using dictionary lookup."""
        words = text.split()
        result = []
        
        for word in words:
            # Skip if already a valid word or too short
            if len(word) <= 4 or self._is_valid_word(word):
                result.append(word)
                continue
            
            # Try to split the word
            split_word = self._split_word(word)
            result.append(split_word)
        
        return ' '.join(result)
    
    def _is_valid_word(self, word: str) -> bool:
        """Check if a word is valid."""
        # Remove punctuation for checking
        clean_word = re.sub(r'[^\w]', '', word)
        
        if not clean_word:
            return True
        
        # Check original case and lowercase
        if clean_word.lower() in self._word_set:
            return True
        
        # Check with spell checker if available
        if self._spell_checker:
            return self._spell_checker.check(clean_word)
        
        return False
    
    def _split_word(self, word: str) -> str:
        """Try to split a concatenated word."""
        # Preserve original case pattern
        original_word = word
        word_lower = word.lower()
        
        # Try all possible split points
        best_split = None
        best_score = -1
        
        for i in range(1, len(word)):
            left = word_lower[:i]
            right = word_lower[i:]
            
            # Score based on both parts being valid words
            score = 0
            if left in self._word_set:
                score += len(left)
            if right in self._word_set:
                score += len(right)
            
            # Bonus for more balanced splits
            balance = 1 - abs(len(left) - len(right)) / len(word)
            score *= balance
            
            if score > best_score:
                best_score = score
                best_split = i
        
        # Only split if we found valid words
        if best_split and best_score > len(word) * 0.8:
            # Preserve original case
            return original_word[:best_split] + ' ' + original_word[best_split:]
        
        return original_word
    
    def _fix_pharma_patterns(self, text: str) -> str:
        """Fix pharmaceutical-specific patterns."""
        replacements = {
            # Common pharma terms that get concatenated
            r'theinformation': 'the information',
            r'neededto': 'needed to',
            r'touse': 'to use',
            r'safelyand': 'safely and',
            r'includeall': 'include all',
            r'donot': 'do not',
            r'forthe': 'for the',
            r'ofthe': 'of the',
            r'tothe': 'to the',
            r'andthe': 'and the',
            r'inthe': 'in the',
            r'isthe': 'is the',
            r'atthe': 'at the',
            # Fix specific drug-related patterns
            r'(\w+)(vaccine|Vaccine)': r'\1 \2',
            r'(\w+)(indicated|Indicated)': r'\1 \2',
            r'(\w+)(approved|Approved)': r'\1 \2',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text


class SmartSpacingFixer(SpacingFixer):
    """Advanced spacing fixer with context awareness."""
    
    def __init__(self):
        """Initialize with medical dictionary."""
        super().__init__(use_dictionary=True)
        self._build_ngram_model()
    
    def _build_ngram_model(self):
        """Build common bigrams and trigrams for context."""
        # Common pharmaceutical bigrams
        self.common_bigrams = {
            ('these', 'highlights'),
            ('do', 'not'),
            ('include', 'all'),
            ('the', 'information'),
            ('needed', 'to'),
            ('to', 'use'),
            ('safely', 'and'),
            ('prescribing', 'information'),
            ('influenza', 'vaccine'),
            ('intramuscular', 'use'),
            ('dosage', 'and'),
            ('and', 'administration'),
            ('dosage', 'forms'),
            ('forms', 'and'),
            ('and', 'strengths'),
            ('indications', 'and'),
            ('and', 'usage'),
            ('severe', 'allergic'),
            ('allergic', 'reactions'),
        }
    
    def fix_spacing_with_context(self, text: str) -> str:
        """Fix spacing using context clues."""
        # First apply basic fixes
        text = self.fix_spacing(text)
        
        # Then apply context-aware fixes
        words = text.split()
        result = []
        
        i = 0
        while i < len(words):
            current_word = words[i]
            
            # Check if current word might be concatenated
            if len(current_word) > 10 and not self._is_valid_word(current_word):
                # Try to split based on known bigrams
                split = self._context_aware_split(current_word)
                if split != current_word:
                    result.extend(split.split())
                else:
                    result.append(current_word)
            else:
                result.append(current_word)
            
            i += 1
        
        return ' '.join(result)
    
    def _context_aware_split(self, word: str) -> str:
        """Split word using context clues."""
        word_lower = word.lower()
        
        # Check all possible bigrams within the word
        for bigram in self.common_bigrams:
            combined = ''.join(bigram)
            if combined in word_lower:
                # Find the position and split
                pos = word_lower.find(combined)
                if pos >= 0:
                    # Calculate where to split within the combined bigram
                    split_point = pos + len(bigram[0])
                    return word[:split_point] + ' ' + word[split_point:]
        
        # Fall back to regular splitting
        return self._split_word(word)


def fix_extracted_text(text: str, aggressive: bool = False) -> str:
    """
    Convenience function to fix spacing in extracted text.
    
    Args:
        text: Text with potential spacing issues
        aggressive: Use more aggressive fixing strategies
        
    Returns:
        Text with improved spacing
    """
    if aggressive:
        fixer = SmartSpacingFixer()
        return fixer.fix_spacing_with_context(text)
    else:
        fixer = SpacingFixer(use_dictionary=False)
        return fixer.fix_spacing(text)