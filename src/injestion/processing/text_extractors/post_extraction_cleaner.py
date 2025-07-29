"""Post-extraction text cleaning for common PDF issues."""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class PostExtractionCleaner:
    """Clean text after extraction to fix common PDF issues."""
    
    def __init__(self):
        """Initialize cleaner with patterns."""
        # Common truncated words in medical documents
        self.truncated_patterns = [
            (r'\bUBLOK\b', 'FLUBLOK'),
            (r'\bNFORMATION\b', 'INFORMATION'),
            (r'\bDMINISTRATION\b', 'ADMINISTRATION'),
            (r'\bONTRAINDICATIONS\b', 'CONTRAINDICATIONS'),
            (r'\bRECAUTIONS\b', 'PRECAUTIONS'),
            (r'\bEACTIONS\b', 'REACTIONS'),
            (r'\bNTERACTIONS\b', 'INTERACTIONS'),
            (r'\bRIBING\b', 'PRESCRIBING'),
            (r'\bATIENT\b', 'PATIENT'),
            (r'\bOUNSELING\b', 'COUNSELING'),
        ]
        
        # Common missing space patterns
        self.missing_space_patterns = [
            # Missing space after period
            (r'\.([A-Z])', r'. \1'),
            # Missing space after comma
            (r',([A-Za-z])', r', \1'),
            # Missing space after colon
            (r':([A-Za-z])', r': \1'),
            # Missing space after semicolon
            (r';([A-Za-z])', r'; \1'),
            # Missing space after closing parenthesis
            (r'\)([A-Za-z])', r') \1'),
        ]
        
        # Gibberish patterns (single letters with spaces)
        self.gibberish_pattern = re.compile(r'(?:\b[a-z]\s){5,}')
        
        # Extreme concatenation patterns
        self.extreme_concat_pattern = re.compile(r'[a-zA-Z]{30,}')
        
    def clean(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return text
            
        original = text
        
        # Step 1: Fix truncated words
        text = self._fix_truncated_words(text)
        
        # Step 2: Fix missing spaces
        text = self._fix_missing_spaces(text)
        
        # Step 3: Remove gibberish
        text = self._remove_gibberish(text)
        
        # Step 4: Fix extreme concatenation
        text = self._fix_extreme_concatenation(text)
        
        # Step 5: Fix specific medical/pharma terms
        text = self._fix_medical_terms(text)
        
        # Step 6: Clean up extra spaces
        text = self._normalize_whitespace(text)
        
        if text != original:
            logger.debug(f"Post-extraction cleaning modified text (len: {len(original)} -> {len(text)})")
        
        return text
    
    def _fix_truncated_words(self, text: str) -> str:
        """Fix common truncated words."""
        for pattern, replacement in self.truncated_patterns:
            text = re.sub(pattern, replacement, text)
        
        # Fix truncated words at line starts (capital letter pattern)
        # e.g., "UBLOK" at start of line should be "FLUBLOK"
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                # Check if line starts with uppercase letters that look truncated
                match = re.match(r'^([A-Z]{3,})\s', line)
                if match:
                    word = match.group(1)
                    # Check our patterns
                    for pattern, replacement in self.truncated_patterns:
                        if re.match(pattern.replace('\\b', '^'), word):
                            line = line.replace(word, replacement, 1)
                            break
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_missing_spaces(self, text: str) -> str:
        """Fix missing spaces after punctuation."""
        for pattern, replacement in self.missing_space_patterns:
            text = re.sub(pattern, replacement, text)
        
        # Fix specific cases like "im anaphylactic" -> "immediate anaphylactic"
        # This requires context-aware fixing
        text = re.sub(r'\bim\s+anaphylactic', 'immediate anaphylactic', text)
        text = re.sub(r'\badminist\b', 'administration', text)
        
        return text
    
    def _remove_gibberish(self, text: str) -> str:
        """Remove or fix gibberish patterns."""
        # Find gibberish patterns
        matches = list(self.gibberish_pattern.finditer(text))
        
        if matches:
            # Remove gibberish sections
            for match in reversed(matches):  # Reverse to maintain positions
                start, end = match.span()
                # Check if it's at the end of a line
                if end < len(text) and text[end] == '\n':
                    # Remove the whole gibberish part
                    text = text[:start] + text[end:]
                else:
                    # Replace with ellipsis to indicate missing text
                    text = text[:start] + '...' + text[end:]
                    
            logger.debug(f"Removed {len(matches)} gibberish sections")
        
        return text
    
    def _fix_extreme_concatenation(self, text: str) -> str:
        """Fix extremely long concatenated words."""
        matches = list(self.extreme_concat_pattern.finditer(text))
        
        for match in matches:
            word = match.group()
            # Skip if it's a URL or similar
            if '://' in word or '@' in word:
                continue
                
            # Try to fix specific patterns
            fixed = word
            
            # Common pharma/medical concatenations
            patterns = [
                (r'inﬂuenza', 'influenza'),
                (r'uenza', 'uenza '),  # Add space after
                (r'vaccine', ' vaccine'),  # Add space before
                (r'approved', ' approved'),
                (r'foruse', 'for use'),
                (r'inthis', 'in this'),
                (r'population', ' population'),
            ]
            
            for pattern, replacement in patterns:
                if pattern in fixed.lower():
                    # Find the pattern case-insensitively and replace
                    regex = re.compile(re.escape(pattern), re.IGNORECASE)
                    fixed = regex.sub(replacement, fixed)
            
            if fixed != word:
                text = text.replace(word, fixed)
                logger.debug(f"Fixed concatenation: {word[:30]}... -> {fixed[:30]}...")
        
        return text
    
    def _fix_medical_terms(self, text: str) -> str:
        """Fix specific medical and pharmaceutical terms."""
        # Fix ligatures
        text = text.replace('ﬂ', 'fl')
        text = text.replace('ﬁ', 'fi')
        text = text.replace('ﬀ', 'ff')
        
        # Fix specific drug names
        text = re.sub(r'Flu\s*blok', 'Flublok', text, flags=re.IGNORECASE)
        
        # Fix dosage patterns
        text = re.sub(r'(\d+\.?\d*)\s*mL', r'\1 mL', text)
        text = re.sub(r'(\d+\.?\d*)\s*mg', r'\1 mg', text)
        text = re.sub(r'(\d+\.?\d*)\s*mcg', r'\1 mcg', text)
        
        # Fix age patterns
        text = re.sub(r'(\d+)\s*years', r'\1 years', text)
        text = re.sub(r'(\d+)\s*months', r'\1 months', text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Remove spaces before punctuation
        text = re.sub(r' ([.,;:!?])', r'\1', text)
        
        # Remove trailing spaces
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        text = '\n'.join(lines)
        
        # Remove multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()


# Singleton instance
post_extraction_cleaner = PostExtractionCleaner()


def clean_extracted_text(text: str) -> str:
    """Clean text after PDF extraction.
    
    This function handles issues that are specific to PDF extraction
    problems, such as:
    - Truncated words at bbox boundaries
    - Missing characters
    - Gibberish from layout detection issues
    - Extreme concatenation
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    return post_extraction_cleaner.clean(text)