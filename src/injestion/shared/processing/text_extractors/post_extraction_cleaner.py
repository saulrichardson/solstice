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
            (r'\bDVERSE\b', 'ADVERSE'),
            (r'\bNDICATIONS\b', 'INDICATIONS'),
            (r'\bOSAGE\b', 'DOSAGE'),
            (r'\bARNINGS\b', 'WARNINGS'),
            (r'\bREGNANCY\b', 'PREGNANCY'),
            (r'\bTORAGE\b', 'STORAGE'),
            (r'\bVERDOSE\b', 'OVERDOSE'),
            (r'\bEDIATRIC\b', 'PEDIATRIC'),
            (r'\bERIATRIC\b', 'GERIATRIC'),
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
        
    def _remove_control_characters(self, text: str) -> str:
        """Remove control characters and clean special characters.
        
        Removes:
        - ASCII control characters (0x00-0x1F) except tab and newline
        - Carriage returns (\r)
        - Zero-width spaces and other invisible Unicode
        - Non-breaking spaces (convert to regular spaces)
        """
        # Remove ASCII control characters except tab (0x09) and newline (0x0A)
        # This includes SOH (0x01), STX (0x02), etc.
        cleaned = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove carriage returns (normalize line endings)
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        
        # Replace non-breaking spaces with regular spaces
        cleaned = cleaned.replace('\u00A0', ' ')
        cleaned = cleaned.replace('\u202F', ' ')  # Narrow no-break space
        cleaned = cleaned.replace('\u2060', '')   # Word joiner (zero-width)
        
        # Remove zero-width characters
        cleaned = cleaned.replace('\u200B', '')  # Zero-width space
        cleaned = cleaned.replace('\u200C', '')  # Zero-width non-joiner
        cleaned = cleaned.replace('\u200D', '')  # Zero-width joiner
        cleaned = cleaned.replace('\uFEFF', '')  # Zero-width no-break space (BOM)
        
        # Replace other special spaces with regular space
        cleaned = re.sub(r'[\u2000-\u200A]', ' ', cleaned)  # Various Unicode spaces
        
        # Replace soft hyphens with nothing (they're invisible)
        cleaned = cleaned.replace('\u00AD', '')
        
        # Replace special quotes and apostrophes with standard ones
        # (This duplicates some work in _fix_medical_terms but it's good to do early)
        cleaned = cleaned.replace('"', '"').replace('"', '"')
        cleaned = cleaned.replace(''', "'").replace(''', "'")
        cleaned = cleaned.replace('`', "'")
        
        # Replace special dashes with standard hyphen
        cleaned = cleaned.replace('–', '-')  # En dash
        cleaned = cleaned.replace('—', '-')  # Em dash
        cleaned = cleaned.replace('‐', '-')  # Hyphen (U+2010)
        cleaned = cleaned.replace('‑', '-')  # Non-breaking hyphen
        
        return cleaned
        
    def clean(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return text
            
        original = text
        
        # Step 0: Remove control characters first
        text = self._remove_control_characters(text)
        
        # Step 1: Fix broken words across lines
        text = self._fix_broken_words(text)
        
        # Step 2: Fix truncated words
        text = self._fix_truncated_words(text)
        
        # Step 3: Fix missing spaces
        text = self._fix_missing_spaces(text)
        
        # Step 4: Remove gibberish
        text = self._remove_gibberish(text)
        
        # Step 5: Fix extreme concatenation
        text = self._fix_extreme_concatenation(text)
        
        # Step 6: Fix specific medical/pharma terms
        text = self._fix_medical_terms(text)
        
        # Step 7: Clean up extra spaces
        text = self._normalize_whitespace(text)
        
        # Step 8: Remove paragraph formatting for LLM processing
        text = self._remove_paragraph_formatting(text)
        
        if text != original:
            logger.debug(f"Post-extraction cleaning modified text (len: {len(original)} -> {len(text)})")
        
        return text
    
    def _fix_broken_words(self, text: str) -> str:
        """Fix words broken across lines."""
        # Pattern: letter + space + single letter + space
        # Like "s antigens which in nhibition"
        
        # Fix specific known breaks
        broken_patterns = [
            (r's\s+antigens\s+which\s+in\s+nhibition', 'antigens which inhibition'),
            (r'in\s+nhibition', 'inhibition'),
            (r'anti\s+bod', 'antibod'),
            (r'h\s+ff\s+t\s+f', 'effect of'),
            (r't\s+isnot', 'it is not'),
            (r'han\s+18', 'than 18'),
        ]
        
        for pattern, replacement in broken_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # General pattern: fix single letters that look broken
        # This is risky but we'll be conservative
        text = re.sub(r'\b([a-z])\s+([a-z]{2,})', r'\1\2', text)
        
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
        
        # Fix specific cases that require context
        context_fixes = [
            # Incomplete words
            (r'\bim\s+anaphylactic', 'immediate anaphylactic'),
            (r'\badminist\b', 'administration'),
            (r'\bdi\s+agnosis', 'diagnosis'),
            (r'\bef\s+fect', 'effect'),
            (r'\bin\s+jection', 'injection'),
            (r'\bvac\s+cine', 'vaccine'),
            (r'\bpa\s+tient', 'patient'),
            (r'\bmed\s+ical', 'medical'),
            
            # Common medical abbreviation spacing
            (r'(\d+)\s*mg\b', r'\1 mg'),
            (r'(\d+)\s*mL\b', r'\1 mL'),
            (r'(\d+)\s*mcg\b', r'\1 mcg'),
            (r'(\d+)\s*%', r'\1%'),
            
            # Fix U.S. patterns
            (r'U\.S\.([a-zA-Z])', r'U.S. \1'),
            (r'Ph\.D\.([a-zA-Z])', r'Ph.D. \1'),
            (r'M\.D\.([a-zA-Z])', r'M.D. \1'),
            
            # Fix common pharma terms
            (r'IIV([0-9])', r'IIV\1'),  # IIV3, IIV4
            (r'RIV([0-9])', r'RIV\1'),  # RIV4
            (r'COVID-?19', 'COVID-19'),
        ]
        
        for pattern, replacement in context_fixes:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
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
        
        # IMPORTANT: Fix "inﬂuenza" → "influenza" (very common)
        text = text.replace('inﬂuenza', 'influenza')
        text = text.replace('INFL UENZA', 'INFLUENZA')
        
        # Fix specific drug names
        text = re.sub(r'Flu\s*blok', 'Flublok', text, flags=re.IGNORECASE)
        
        # Fix dosage patterns with more variations
        text = re.sub(r'(\d+\.?\d*)\s*mL\s*dose', r'\1 mL dose', text)
        text = re.sub(r'(\d+\.?\d*)\s*mL', r'\1 mL', text)
        text = re.sub(r'(\d+\.?\d*)\s*mg', r'\1 mg', text)
        text = re.sub(r'(\d+\.?\d*)\s*mcg\s*HA', r'\1 mcg HA', text)
        text = re.sub(r'(\d+\.?\d*)\s*mcg', r'\1 mcg', text)
        
        # Fix age patterns
        text = re.sub(r'(\d+)\s*years', r'\1 years', text)
        text = re.sub(r'(\d+)\s*months', r'\1 months', text)
        
        # Fix common medical concatenations
        text = re.sub(r'([a-z])viral', r'\1 viral', text)
        text = re.sub(r'([a-z])vaccine', r'\1 vaccine', text)
        text = re.sub(r'([a-z])virus', r'\1 virus', text)
        text = re.sub(r'([a-z])strains?', r'\1 strains', text)
        text = re.sub(r'([a-z])season', r'\1 season', text)
        
        # Fix number+word concatenations
        text = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', text)
        
        # Fix specific patterns from the example
        text = re.sub(r'isthevirologicbasisfor', 'is the virologic basis for', text)
        text = re.sub(r'moreinﬂuenzavirusstrains', 'more influenza virus strains', text)
        text = re.sub(r'formulated\s*to\s*contain(\d+)', r'formulated to contain \1', text)
        text = re.sub(r'with(\d+)', r'with \1', text)
        text = re.sub(r'thefollowing(\d+)', r'the following \1', text)
        
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
    
    def _remove_paragraph_formatting(self, text: str) -> str:
        """Remove paragraph formatting for LLM processing.
        
        Converts multi-line text to continuous text suitable for LLM processing.
        Preserves sentence boundaries but removes visual formatting.
        """
        # Replace multiple newlines with a space (paragraph breaks)
        text = re.sub(r'\n\n+', ' ', text)
        
        # Replace single newlines with spaces, but be smart about it
        # Don't add space if the line ends with a hyphen (word continuation)
        lines = text.split('\n')
        merged_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            if merged_lines and merged_lines[-1].endswith('-'):
                # Remove hyphen and concatenate
                merged_lines[-1] = merged_lines[-1][:-1] + line
            elif merged_lines and merged_lines[-1] and not merged_lines[-1][-1] in '.!?:;':
                # Previous line doesn't end with sentence terminator, add space
                merged_lines[-1] += ' ' + line
            else:
                merged_lines.append(line)
        
        text = ' '.join(merged_lines)
        
        # Clean up any double spaces created
        text = re.sub(r' +', ' ', text)
        
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