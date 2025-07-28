"""Text normalization utilities for quote matching."""

import re
import unicodedata
from typing import List, Callable, Optional
from abc import ABC, abstractmethod


class NormalizationStrategy(ABC):
    """Base class for text normalization strategies."""
    
    @abstractmethod
    def normalize(self, text: str) -> str:
        """Normalize the text according to this strategy."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this normalization strategy."""
        pass


class WhitespaceNormalizer(NormalizationStrategy):
    """Normalize whitespace (spaces, tabs, newlines)."""
    
    def normalize(self, text: str) -> str:
        # Replace all whitespace sequences with single space
        return " ".join(text.split())
    
    @property
    def name(self) -> str:
        return "whitespace"


class PunctuationNormalizer(NormalizationStrategy):
    """Normalize punctuation (remove or standardize)."""
    
    def __init__(self, remove: bool = False):
        self.remove = remove
    
    def normalize(self, text: str) -> str:
        if self.remove:
            # Remove all punctuation
            return re.sub(r'[^\w\s]', '', text)
        else:
            # Standardize quotes and dashes
            text = re.sub(r'["""]', '"', text)
            text = re.sub(r"[''']", "'", text)
            text = re.sub(r'[–—−]', '-', text)
            return text
    
    @property
    def name(self) -> str:
        return f"punctuation_{'remove' if self.remove else 'standardize'}"


class CaseNormalizer(NormalizationStrategy):
    """Normalize case to lowercase."""
    
    def normalize(self, text: str) -> str:
        return text.lower()
    
    @property
    def name(self) -> str:
        return "lowercase"


class UnicodeNormalizer(NormalizationStrategy):
    """Normalize unicode characters."""
    
    def normalize(self, text: str) -> str:
        # NFD normalization then remove accents
        nfd = unicodedata.normalize('NFD', text)
        return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    @property
    def name(self) -> str:
        return "unicode"


class HyphenationNormalizer(NormalizationStrategy):
    """Remove hyphenation at line breaks."""
    
    def normalize(self, text: str) -> str:
        # Remove hyphens at end of lines (common in PDFs)
        text = re.sub(r'-\s*\n\s*', '', text)
        # Also handle cases with just hyphen-space
        text = re.sub(r'([a-z])-\s+([a-z])', r'\1\2', text, flags=re.IGNORECASE)
        return text
    
    @property
    def name(self) -> str:
        return "hyphenation"


class NumberNormalizer(NormalizationStrategy):
    """Normalize number formats."""
    
    def normalize(self, text: str) -> str:
        # Remove commas from numbers
        text = re.sub(r'(\d),(\d)', r'\1\2', text)
        # Standardize percentages
        text = re.sub(r'(\d)\s*%', r'\1%', text)
        return text
    
    @property
    def name(self) -> str:
        return "numbers"


class LigatureNormalizer(NormalizationStrategy):
    """Normalize common ligatures from PDF extraction."""
    
    def normalize(self, text: str) -> str:
        # Common ligatures to their expanded forms
        ligatures = {
            'ﬁ': 'fi',
            'ﬂ': 'fl',
            'ﬀ': 'ff',
            'ﬃ': 'ffi',
            'ﬄ': 'ffl',
            'ﬅ': 'st',
            'ﬆ': 'st',
            # Add more as needed
        }
        
        for ligature, replacement in ligatures.items():
            text = text.replace(ligature, replacement)
        
        return text
    
    @property
    def name(self) -> str:
        return "ligatures"


class TextNormalizer:
    """Applies multiple normalization strategies to text."""
    
    def __init__(self, strategies: Optional[List[NormalizationStrategy]] = None):
        """
        Initialize with normalization strategies.
        
        Args:
            strategies: List of strategies to apply. If None, uses defaults.
        """
        if strategies is None:
            strategies = [
                WhitespaceNormalizer(),
                PunctuationNormalizer(remove=False),
                HyphenationNormalizer(),
                NumberNormalizer(),
                LigatureNormalizer()
            ]
        self.strategies = strategies
    
    def normalize(self, text: str) -> str:
        """Apply all normalization strategies in sequence."""
        result = text
        for strategy in self.strategies:
            result = strategy.normalize(result)
        return result
    
    def normalize_with_levels(self, text: str) -> List[tuple[str, List[str]]]:
        """
        Apply normalization progressively, returning results at each level.
        
        Returns:
            List of (normalized_text, strategies_applied) tuples
        """
        results = [(text, [])]
        current = text
        applied = []
        
        for strategy in self.strategies:
            current = strategy.normalize(current)
            applied.append(strategy.name)
            results.append((current, applied.copy()))
        
        return results


def get_aggressive_normalizer() -> TextNormalizer:
    """Get a normalizer with aggressive normalization for difficult matches."""
    return TextNormalizer([
        WhitespaceNormalizer(),
        PunctuationNormalizer(remove=True),
        CaseNormalizer(),
        HyphenationNormalizer(),
        NumberNormalizer(),
        UnicodeNormalizer()
    ])


def get_default_normalizer() -> TextNormalizer:
    """Get the default normalizer with moderate normalization."""
    return TextNormalizer()