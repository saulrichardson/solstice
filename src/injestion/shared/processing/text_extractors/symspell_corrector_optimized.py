"""Optimized SymSpellPy-based text corrector for medical/pharmaceutical documents.

This version is optimized for performance while maintaining accuracy.
"""

import logging
import re
from pathlib import Path
from typing import List, Set, Optional, Dict
import os

from symspellpy import SymSpell, Verbosity

logger = logging.getLogger(__name__)


class OptimizedSymSpellCorrector:
    """Optimized text corrector using SymSpellPy."""
    
    # Class-level shared instance for dictionary reuse
    _shared_symspell: Optional['SymSpell'] = None
    _initialized: bool = False
    
    def __init__(self, 
                 max_edit_distance: int = 2,
                 prefix_length: int = 7,
                 use_segmentation: bool = True):
        """Initialize SymSpell corrector.
        
        Args:
            max_edit_distance: Maximum edit distance for corrections
            prefix_length: Prefix length for internal data structure
            use_segmentation: Whether to use word segmentation
        """
        
        self.max_edit_distance = max_edit_distance
        self.use_segmentation = use_segmentation
        
        # Use shared dictionary instance
        if OptimizedSymSpellCorrector._shared_symspell is None:
            OptimizedSymSpellCorrector._shared_symspell = SymSpell(max_edit_distance, prefix_length)
            self.sym_spell = OptimizedSymSpellCorrector._shared_symspell
            self._initialize_dictionary()
            OptimizedSymSpellCorrector._initialized = True
        else:
            self.sym_spell = OptimizedSymSpellCorrector._shared_symspell
        
        # Precompiled patterns for performance
        self._init_patterns()
        
        # Cache for common corrections
        self._correction_cache: Dict[str, str] = {}
        
    def _initialize_dictionary(self):
        """Initialize dictionary only once."""
        # Find and load the built-in English dictionary
        import symspellpy
        package_dir = Path(symspellpy.__file__).parent
        dict_file = package_dir / "frequency_dictionary_en_82_765.txt"
        
        if not dict_file.exists():
            raise FileNotFoundError(f"SymSpell dictionary not found at {dict_file}")
            
        self.sym_spell.load_dictionary(str(dict_file), 0, 1)
        logger.info(f"Loaded dictionary from {dict_file}")
        
        # Add medical terms with high frequency
        self._add_medical_terms_optimized()
    
    def _add_medical_terms_optimized(self):
        """Add only essential medical terms for performance."""
        # Core medical terms with high frequency
        essential_terms = [
            # Most common medical terms
            "vaccine", "influenza", "dose", "injection", "virus", "clinical",
            "adverse", "reaction", "administration", "contraindication",
            "immunization", "antibody", "antigen", "efficacy", "safety",
            
            # Units and measures
            "ml", "mg", "mcg", "years", "months", "days",
            
            # Common pharmaceuticals
            "flublok", "fluzone", "fluarix",
            
            # Technical terms
            "hemagglutinin", "quadrivalent", "trivalent", "inactivated",
            "intramuscular", "subcutaneous", "formulated", "contains"
        ]
        
        # Add with high frequency for priority
        for term in essential_terms:
            self.sym_spell.create_dictionary_entry(term.lower(), 10000)
    
    def _init_patterns(self):
        """Initialize precompiled regex patterns."""
        # Simple patterns that don't need SymSpell
        self.simple_fixes = [
            # Common concatenations
            (re.compile(r'\bisthe\b', re.I), 'is the'),
            (re.compile(r'\bofthe\b', re.I), 'of the'),
            (re.compile(r'\btothe\b', re.I), 'to the'),
            (re.compile(r'\binthe\b', re.I), 'in the'),
            (re.compile(r'\bforthe\b', re.I), 'for the'),
            (re.compile(r'\bandthe\b', re.I), 'and the'),
            (re.compile(r'\bfromthe\b', re.I), 'from the'),
            (re.compile(r'\bwiththe\b', re.I), 'with the'),
            (re.compile(r'\boneor\b', re.I), 'one or'),
            (re.compile(r'\btwoor\b', re.I), 'two or'),
            
            # Units
            (re.compile(r'(\d+\.?\d*)mL'), r'\1 mL'),
            (re.compile(r'(\d+\.?\d*)mg'), r'\1 mg'),
            (re.compile(r'(\d+\.?\d*)mcg'), r'\1 mcg'),
            (re.compile(r'(\d+)years'), r'\1 years'),
            (re.compile(r'(\d+)months'), r'\1 months'),
        ]
        
        # Ligature replacements
        self.ligatures = str.maketrans({
            'ﬂ': 'fl', 'ﬁ': 'fi', 'ﬀ': 'ff', 
            'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'st'
        })
    
    def correct_text(self, text: str) -> str:
        """Correct text using optimized approach.
        
        Args:
            text: Input text with potential errors
            
        Returns:
            Corrected text
        """
        if not text or len(text) < 3:
            return text
        
        # Step 1: Fast ligature fix
        text = text.translate(self.ligatures)
        
        # Step 2: Apply simple pattern fixes (very fast)
        for pattern, replacement in self.simple_fixes:
            text = pattern.sub(replacement, text)
        
        # Step 3: Only use SymSpell for remaining complex issues
        if self.use_segmentation and self._needs_segmentation(text):
            text = self._selective_segmentation(text)
        
        return text
    
    def _needs_segmentation(self, text: str) -> bool:
        """Check if text needs word segmentation."""
        # Quick heuristics to avoid unnecessary processing
        words = text.split()
        
        # Check for suspiciously long words
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if len(clean_word) > 15 and clean_word.isalpha():
                return True
        
        # Check for known problem patterns
        problem_patterns = [
            'virusstrains', 'vaccineis', 'dosecontains',
            'informationneeded', 'highlightsdonot',
            'isthe', 'ofthe', 'tothe', 'forthe', 'andthe',
            'oneor', 'twoor', 'threeor', 'formulatedto',
            'virologicbasisfor', 'influenzavirus'
        ]
        
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in problem_patterns)
    
    def _selective_segmentation(self, text: str) -> str:
        """Apply segmentation only to problematic parts."""
        words = text.split()
        result = []
        
        for word in words:
            # Extract punctuation
            clean_word = re.sub(r'[^\w]', '', word)
            
            # Skip if too short or has numbers
            if len(clean_word) < 6 or not clean_word.isalpha():
                result.append(word)
                continue
            
            # Check cache first
            cache_key = clean_word.lower()
            if cache_key in self._correction_cache:
                corrected = self._correction_cache[cache_key]
                # Restore original case
                if clean_word.isupper():
                    corrected = corrected.upper()
                elif clean_word[0].isupper():
                    corrected = corrected.capitalize()
                result.append(word.replace(clean_word, corrected))
                continue
            
            # Try segmentation for concatenated words
            if len(clean_word) > 6:
                segmented = self._segment_word(clean_word)
                if segmented != clean_word:
                    self._correction_cache[cache_key] = segmented.lower()
                    result.append(word.replace(clean_word, segmented))
                    continue
            
            result.append(word)
        
        return ' '.join(result)
    
    def _segment_word(self, word: str) -> str:
        """Segment a single word if needed."""
        # Try word segmentation with minimal edit distance
        result = self.sym_spell.word_segmentation(word.lower(), max_edit_distance=0)
        
        if result and ' ' in result.corrected_string:
            parts = result.corrected_string.split()
            
            # Quick validation
            if len(parts) <= 5 and all(len(p) > 1 or p in 'ai' for p in parts):
                # Restore case
                if word.isupper():
                    return ' '.join(p.upper() for p in parts)
                elif word[0].isupper():
                    parts[0] = parts[0].capitalize()
                    return ' '.join(parts)
                return result.corrected_string
        
        return word


# Global instance for reuse
_global_corrector: Optional[OptimizedSymSpellCorrector] = None


def correct_medical_text_optimized(text: str) -> str:
    """
    Optimized medical text correction using SymSpell.
    
    Args:
        text: Text to correct
        
    Returns:
        Corrected text
    """
    global _global_corrector
    
    if _global_corrector is None:
        _global_corrector = OptimizedSymSpellCorrector()
    
    return _global_corrector.correct_text(text)