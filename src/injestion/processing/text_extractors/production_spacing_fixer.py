"""Production-ready spacing fixer for PyMuPDF extracted text."""

import re
from typing import Set, List, Tuple


class PyMuPDFSpacingFixer:
    """Conservative spacing fixer specifically for PyMuPDF extraction issues."""
    
    def __init__(self):
        """Initialize with known problematic patterns."""
        # Only fix patterns we're absolutely sure about
        self.definite_fixes = {
            # Common concatenations in pharmaceutical texts
            'thesehighlight': 'these highlight',
            'donot': 'do not',
            'includeall': 'include all',
            'theinformation': 'the information',
            'neededto': 'needed to',
            'touse': 'to use',
            'safelyand': 'safely and',
            'tothe': 'to the',
            'ofthe': 'of the',
            'forthe': 'for the',
            'andthe': 'and the',
            'inthe': 'in the',
            'isthe': 'is the',
            'atthe': 'at the',
            'onthe': 'on the',
            'ahistory': 'a history',
            'avaccine': 'a vaccine',
            'asingle': 'a single',
            'asevere': 'a severe',
            # Add more as discovered
        }
    
    def fix_spacing(self, text: str) -> str:
        """Apply conservative spacing fixes."""
        # Step 1: Fix punctuation spacing (very safe)
        text = self._fix_punctuation_spacing(text)
        
        # Step 2: Fix known problematic concatenations
        text = self._fix_known_concatenations(text)
        
        # Step 3: Fix obvious camelCase
        text = self._fix_obvious_camel_case(text)
        
        # Step 4: Fix number-unit spacing
        text = self._fix_units(text)
        
        # Step 5: Fix specific patterns
        text = self._fix_specific_patterns(text)
        
        # Clean up multiple spaces
        text = ' '.join(text.split())
        
        return text
    
    def _fix_punctuation_spacing(self, text: str) -> str:
        """Fix spacing around punctuation - very safe."""
        # Add space after sentence-ending punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        # Add space after comma and semicolon
        text = re.sub(r'([,;])([A-Za-z])', r'\1 \2', text)
        
        # Add space after colon if followed by letter
        text = re.sub(r':([A-Za-z])', r': \1', text)
        
        # Add space after closing parenthesis
        text = re.sub(r'\)([A-Za-z])', r') \1', text)
        
        # Add space before opening parenthesis
        text = re.sub(r'([A-Za-z])\(', r'\1 (', text)
        
        return text
    
    def _fix_known_concatenations(self, text: str) -> str:
        """Fix only known problematic concatenations."""
        text_lower = text.lower()
        
        # Apply fixes while preserving case
        for pattern, replacement in self.definite_fixes.items():
            # Find all occurrences case-insensitively
            for match in re.finditer(pattern, text_lower):
                start, end = match.span()
                original = text[start:end]
                
                # Preserve the original case pattern
                if original.isupper():
                    fixed = replacement.upper()
                elif original[0].isupper():
                    fixed = replacement[0].upper() + replacement[1:]
                else:
                    fixed = replacement
                
                # Replace in original text
                text = text[:start] + fixed + text[end:]
                # Update lowercase version for next iteration
                text_lower = text.lower()
        
        return text
    
    def _fix_obvious_camel_case(self, text: str) -> str:
        """Fix only obvious camelCase patterns."""
        # Only split when lowercase letter is followed by uppercase letter
        # and the result would be two meaningful parts
        
        # List of known camelCase patterns in pharmaceutical texts
        known_camel_patterns = [
            (r'(\w+)(Vaccine)', r'\1 \2'),
            (r'(\w+)(Injection)', r'\1 \2'),
            (r'(\w+)(Formula)', r'\1 \2'),
            (r'(\w+)(Approval)', r'\1 \2'),
            (r'(\w+)(Administration)', r'\1 \2'),
            (r'(\w+)(Information)', r'\1 \2'),
            (r'(Flublok)([a-z])', r'\1 \2'),  # Flublokto -> Flublok to
        ]
        
        for pattern, replacement in known_camel_patterns:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    def _fix_units(self, text: str) -> str:
        """Fix spacing between numbers and units."""
        # Common medical units
        units = ['mL', 'mg', 'mcg', 'IU', 'L', 'g', 'kg']
        
        for unit in units:
            # Add space between number and unit
            text = re.sub(rf'(\d+\.?\d*)({unit})\b', rf'\1 \2', text)
        
        # Fix year patterns like "18years"
        text = re.sub(r'(\d+)(years?|months?|days?|weeks?|hours?)', r'\1 \2', text)
        
        return text
    
    def _fix_specific_patterns(self, text: str) -> str:
        """Fix specific patterns found in pharmaceutical documents."""
        # Fix "Use2024-2025" -> "Use 2024-2025"
        text = re.sub(r'(Use)(\d{4})', r'\1 \2', text)
        
        # Fix "Approval:2013" -> "Approval: 2013"
        text = re.sub(r'(Approval:)(\d{4})', r'\1 \2', text)
        
        # Fix U.S.A patterns
        text = re.sub(r'U\.S\.([A-Z])', r'U.S. \1', text)
        
        # Fix specific drug name patterns
        text = re.sub(r'(Flublok®)(safely)', r'\1 \2', text)
        
        # Fix "18years of age" patterns
        text = re.sub(r'(\d+years) (of) (age)', r'\1 \2 \3', text)
        
        return text


def fix_pymupdf_spacing(text: str) -> str:
    """
    Fix common spacing issues in PyMuPDF extracted text.
    
    This is a conservative approach that only fixes patterns
    we're confident about, to avoid breaking correctly
    formatted text.
    
    Args:
        text: Text extracted by PyMuPDF
        
    Returns:
        Text with improved spacing
    """
    fixer = PyMuPDFSpacingFixer()
    return fixer.fix_spacing(text)


# Enhanced version with learning capability
class AdaptiveSpacingFixer(PyMuPDFSpacingFixer):
    """Spacing fixer that can learn from corrections."""
    
    def __init__(self):
        super().__init__()
        self.learned_patterns = {}
    
    def learn_from_comparison(self, pymupdf_text: str, correct_text: str):
        """Learn spacing patterns by comparing PyMuPDF output with correct text."""
        # This could be extended to learn new patterns
        # For now, just identify missing spaces
        
        pymupdf_words = pymupdf_text.lower().split()
        correct_words = correct_text.lower().split()
        
        # Find concatenated words
        for p_word in pymupdf_words:
            if len(p_word) > 10:  # Likely concatenated
                # Check if it appears as multiple words in correct text
                for i in range(len(correct_words) - 1):
                    combined = correct_words[i] + correct_words[i + 1]
                    if combined == p_word:
                        # Found a pattern
                        self.learned_patterns[p_word] = f"{correct_words[i]} {correct_words[i + 1]}"
                        break
    
    def fix_spacing(self, text: str) -> str:
        """Apply fixes including learned patterns."""
        # First apply standard fixes
        text = super().fix_spacing(text)
        
        # Then apply learned patterns
        for pattern, replacement in self.learned_patterns.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text