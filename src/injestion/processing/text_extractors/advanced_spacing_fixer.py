"""Advanced spacing fixers using NLP and ML approaches."""

import re
from typing import List, Tuple, Optional
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import words, brown
from nltk.probability import FreqDist
from nltk.util import ngrams
import enchant
from symspellpy import SymSpell, Verbosity
from wordninja import split as wordninja_split
import language_tool_python


class WordSegmentationFixer:
    """Fix spacing using word segmentation algorithms."""
    
    def __init__(self):
        """Initialize with word frequency data."""
        # Download required NLTK data
        for resource in ['words', 'brown', 'punkt']:
            try:
                nltk.data.find(f'corpora/{resource}')
            except LookupError:
                nltk.download(resource)
        
        # Build word frequency dictionary from Brown corpus
        self.word_freq = self._build_frequency_dict()
        
        # Initialize spell checker
        self.spell_checker = enchant.Dict("en_US")
        
        # Initialize WordNinja (uses Google word frequencies)
        # WordNinja is great for splitting concatenated words
        
    def _build_frequency_dict(self):
        """Build word frequency dictionary from corpus."""
        # Use Brown corpus for word frequencies
        brown_words = brown.words()
        freq_dist = FreqDist(word.lower() for word in brown_words)
        
        # Add medical/pharma terms
        medical_terms = {
            'vaccine', 'influenza', 'immunization', 'intramuscular',
            'contraindications', 'anaphylaxis', 'prescribing', 'dosage',
            'administration', 'flublok', 'highlights', 'information'
        }
        
        for term in medical_terms:
            freq_dist[term] = 1000  # Give high frequency to medical terms
        
        return freq_dist
    
    def fix_spacing_wordninja(self, text: str) -> str:
        """Use WordNinja for word segmentation."""
        words = text.split()
        result = []
        
        for word in words:
            # Skip short words or numbers
            if len(word) <= 4 or word.isdigit():
                result.append(word)
                continue
            
            # Check if it's a valid word
            if self.spell_checker.check(word.lower()):
                result.append(word)
                continue
            
            # Try to split concatenated words
            split_words = wordninja_split(word.lower())
            
            # Preserve original capitalization pattern
            if word[0].isupper():
                split_words[0] = split_words[0].capitalize()
            
            result.extend(split_words)
        
        return ' '.join(result)
    
    def fix_spacing_viterbi(self, text: str) -> str:
        """Use Viterbi algorithm for word segmentation."""
        # Implementation of Viterbi algorithm for word segmentation
        # This finds the most likely sequence of words
        
        def word_probability(word):
            """Calculate word probability based on frequency."""
            return self.word_freq.get(word.lower(), 0) / sum(self.word_freq.values())
        
        def segment(text):
            """Segment text using dynamic programming."""
            if not text:
                return []
            
            # Dynamic programming table
            best_score = [0] * (len(text) + 1)
            best_cut = [0] * (len(text) + 1)
            
            for i in range(1, len(text) + 1):
                best_score[i] = float('-inf')
                for j in range(max(0, i - 20), i):  # Max word length 20
                    word = text[j:i]
                    if word.lower() in self.word_freq or self.spell_checker.check(word):
                        score = best_score[j] + log(word_probability(word) + 1e-10)
                        if score > best_score[i]:
                            best_score[i] = score
                            best_cut[i] = j
            
            # Backtrack to find segmentation
            words = []
            i = len(text)
            while i > 0:
                j = best_cut[i]
                words.append(text[j:i])
                i = j
            
            return list(reversed(words))
        
        from math import log
        
        # Process each space-separated token
        tokens = text.split()
        result = []
        
        for token in tokens:
            if len(token) > 10 and not self.spell_checker.check(token):
                segmented = segment(token)
                result.extend(segmented)
            else:
                result.append(token)
        
        return ' '.join(result)


class SymSpellFixer:
    """Fix spacing using SymSpell compound splitting."""
    
    def __init__(self):
        """Initialize SymSpell with dictionary."""
        self.sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        
        # Load frequency dictionary
        # You would need to download a frequency dictionary file
        # Example: frequency_dictionary_en_82_765.txt from SymSpell repo
        dict_path = "frequency_dictionary_en_82_765.txt"
        
        try:
            self.sym_spell.load_dictionary(dict_path, term_index=0, count_index=1)
            self.initialized = True
        except FileNotFoundError:
            print("SymSpell dictionary not found. Download from:")
            print("https://github.com/wolfgarbe/SymSpell/tree/master/SymSpell.FrequencyDictionary")
            self.initialized = False
    
    def fix_spacing(self, text: str) -> str:
        """Fix spacing using SymSpell compound splitting."""
        if not self.initialized:
            return text
        
        # Split compounds and correct spelling
        suggestions = self.sym_spell.word_segmentation(text, max_edit_distance=0)
        
        if suggestions:
            return suggestions.segmented_string
        
        return text


class LanguageToolFixer:
    """Fix spacing using LanguageTool grammar checker."""
    
    def __init__(self):
        """Initialize LanguageTool."""
        self.tool = language_tool_python.LanguageTool('en-US')
    
    def fix_spacing(self, text: str) -> str:
        """Fix spacing using LanguageTool."""
        # Get all matches (errors)
        matches = self.tool.check(text)
        
        # Apply corrections
        corrected = language_tool_python.utils.correct(text, matches)
        
        return corrected
    
    def __del__(self):
        """Clean up LanguageTool."""
        if hasattr(self, 'tool'):
            self.tool.close()


class MLSpacingFixer:
    """Fix spacing using machine learning approaches."""
    
    def __init__(self, use_transformers: bool = False):
        """Initialize ML-based fixer."""
        self.use_transformers = use_transformers
        
        if use_transformers:
            try:
                from transformers import pipeline
                # Use a fill-mask model to predict spaces
                self.mask_model = pipeline("fill-mask", model="bert-base-uncased")
            except ImportError:
                print("Transformers not installed. Install with: pip install transformers")
                self.use_transformers = False
    
    def fix_spacing_with_bert(self, text: str) -> str:
        """Use BERT to predict where spaces should go."""
        if not self.use_transformers:
            return text
        
        # This is a simplified approach
        # In practice, you'd need a model specifically trained for space insertion
        
        # For demonstration: insert [MASK] tokens and predict
        # This would need more sophisticated implementation
        
        return text


class HybridSpacingFixer:
    """Combine multiple approaches for best results."""
    
    def __init__(self):
        """Initialize all fixers."""
        print("Initializing hybrid spacing fixer...")
        
        # Initialize different approaches
        self.segmentation_fixer = WordSegmentationFixer()
        # self.symspell_fixer = SymSpellFixer()  # Requires dictionary file
        # self.language_tool = LanguageToolFixer()  # May be slow
        
        # Use WordNinja as primary method (it's quite good)
        import wordninja
        self.wordninja = wordninja
    
    def fix_spacing(self, text: str) -> str:
        """Apply best combination of fixes."""
        # Step 1: Fix obvious punctuation issues
        text = self._fix_punctuation(text)
        
        # Step 2: Split concatenated words using WordNinja
        words = text.split()
        fixed_words = []
        
        for word in words:
            # Skip short words, numbers, or already valid words
            if len(word) <= 5 or word.isdigit() or self._is_valid_word(word):
                fixed_words.append(word)
                continue
            
            # Use WordNinja to split
            split = self.wordninja.split(word.lower())
            
            # Preserve capitalization of first letter
            if word[0].isupper() and split:
                split[0] = split[0].capitalize()
            
            # Check if split makes sense
            if len(split) > 1 and all(len(w) > 1 for w in split):
                fixed_words.extend(split)
            else:
                fixed_words.append(word)
        
        return ' '.join(fixed_words)
    
    def _fix_punctuation(self, text: str) -> str:
        """Fix punctuation spacing."""
        # Add space after punctuation
        text = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)
        # Add space around parentheses
        text = re.sub(r'\)([A-Za-z])', r') \1', text)
        text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
        return text
    
    def _is_valid_word(self, word: str) -> bool:
        """Check if word is valid."""
        # Simple check - could use enchant or other dictionary
        common_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 
            'for', 'not', 'with', 'you', 'this', 'but', 'from', 'they'
        }
        return word.lower() in common_words or len(word) <= 3


# Example usage functions
def fix_spacing_best_method(text: str) -> str:
    """Use the best available method to fix spacing."""
    try:
        # Try WordNinja first (usually best for concatenated words)
        import wordninja
        
        def fix_with_wordninja(text):
            words = text.split()
            result = []
            
            for word in words:
                if len(word) > 8 and not word.istitle():
                    # Split concatenated words
                    split = wordninja.split(word.lower())
                    
                    # Handle capitalization
                    if word[0].isupper():
                        split[0] = split[0].capitalize()
                    
                    # Handle all caps
                    if word.isupper():
                        split = [w.upper() for w in split]
                    
                    result.extend(split)
                else:
                    result.append(word)
            
            return ' '.join(result)
        
        return fix_with_wordninja(text)
        
    except ImportError:
        # Fallback to simple pattern matching
        from .production_spacing_fixer import fix_pymupdf_spacing
        return fix_pymupdf_spacing(text)