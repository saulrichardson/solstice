"""Smart spacing fixer using heuristics and common patterns."""

import re
from typing import List, Dict, Set, Optional, Tuple


class SmartSpacingFixer:
    """Fix spacing issues using intelligent heuristics."""
    
    def __init__(self):
        """Initialize with comprehensive word patterns."""
        # Build comprehensive word patterns
        self._build_word_patterns()
    
    def _build_word_patterns(self):
        """Build patterns for common word combinations."""
        # Common concatenated patterns in pharmaceutical documents
        self.concat_patterns = [
            # Common phrases
            (r'\b(these)(highlights)\b', r'\1 \2'),
            (r'\b(do)(not)\b', r'\1 \2'),
            (r'\b(include)(all)\b', r'\1 \2'),
            (r'\b(the)(information)\b', r'\1 \2'),
            (r'\b(needed)(to)\b', r'\1 \2'),
            (r'\b(to)(use)\b', r'\1 \2'),
            (r'\b(safely)(and)\b', r'\1 \2'),
            (r'\b(prescribing)(information)\b', r'\1 \2'),
            (r'\b(influenza)(vaccine)\b', r'\1 \2'),
            (r'\b(intramuscular)(use)\b', r'\1 \2'),
            (r'\b(dosage)(and)\b', r'\1 \2'),
            (r'\b(and)(administration)\b', r'\1 \2'),
            (r'\b(dosage)(forms)\b', r'\1 \2'),
            (r'\b(forms)(and)\b', r'\1 \2'),
            (r'\b(and)(strengths)\b', r'\1 \2'),
            (r'\b(indications)(and)\b', r'\1 \2'),
            (r'\b(and)(usage)\b', r'\1 \2'),
            (r'\b(severe)(allergic)\b', r'\1 \2'),
            (r'\b(allergic)(reactions)\b', r'\1 \2'),
            (r'\b(for)(the)\b', r'\1 \2'),
            (r'\b(of)(the)\b', r'\1 \2'),
            (r'\b(to)(the)\b', r'\1 \2'),
            (r'\b(and)(the)\b', r'\1 \2'),
            (r'\b(in)(the)\b', r'\1 \2'),
            (r'\b(is)(the)\b', r'\1 \2'),
            (r'\b(at)(the)\b', r'\1 \2'),
            (r'\b(on)(the)\b', r'\1 \2'),
            
            # Medical specific
            (r'\b(a)(vaccine)\b', r'\1 \2'),
            (r'\b(a)(history)\b', r'\1 \2'),
            (r'\b(with)(a)\b', r'\1 \2'),
            (r'\b(is)(a)\b', r'\1 \2'),
            (r'\b(years)(of)\b', r'\1 \2'),
            (r'\b(of)(age)\b', r'\1 \2'),
            (r'\b(years)(old)\b', r'\1 \2'),
            
            # Fix specific concatenations
            (r'theinformation', r'the information'),
            (r'neededto', r'needed to'),
            (r'touse', r'to use'),
            (r'tothe', r'to the'),
            (r'ofthe', r'of the'),
            (r'forthe', r'for the'),
            (r'andthe', r'and the'),
            (r'inthe', r'in the'),
            (r'includeall', r'include all'),
            (r'safelyand', r'safely and'),
            (r'donot', r'do not'),
            (r'isnot', r'is not'),
            (r'arenot', r'are not'),
            (r'wasnot', r'was not'),
            (r'werenot', r'were not'),
            (r'willnot', r'will not'),
            (r'cannot', r'can not'),
            (r'shouldnot', r'should not'),
            (r'doesnot', r'does not'),
            (r'didnot', r'did not'),
            (r'hasnot', r'has not'),
            (r'havenot', r'have not'),
            (r'hadnot', r'had not'),
            
            # Fix words ending with 'to' + another word
            (r'(\w+to)([a-z]+)', lambda m: self._split_to_pattern(m)),
            
            # Fix concatenated prepositions
            (r'(\w+)(of|for|to|in|on|at|by|with)([A-Z])', r'\1 \2 \3'),
        ]
        
        # Specific word boundaries that should be preserved
        self.preserve_words = {
            'information', 'vaccination', 'administration', 'contraindications',
            'immunization', 'intramuscular', 'anaphylaxis', 'prescribing',
            'influenza', 'vaccine', 'injection', 'approval', 'formula',
            'highlights', 'flublok', 'effectively', 'indicated', 'prevention'
        }
    
    def _split_to_pattern(self, match):
        """Handle words ending with 'to' followed by another word."""
        full = match.group(0)
        prefix = match.group(1)[:-2]  # Remove 'to'
        suffix = match.group(2)
        
        # Check if it's a valid split
        if len(prefix) >= 3 and len(suffix) >= 3:
            return prefix + ' to ' + suffix
        return full
    
    def fix_spacing(self, text: str) -> str:
        """Fix spacing issues in text."""
        # Step 1: Fix obvious punctuation spacing
        text = self._fix_punctuation_spacing(text)
        
        # Step 2: Fix camelCase
        text = self._fix_camel_case(text)
        
        # Step 3: Apply pattern-based fixes
        text = self._apply_patterns(text)
        
        # Step 4: Fix number spacing
        text = self._fix_number_spacing(text)
        
        # Step 5: Fix specific problematic patterns
        text = self._fix_specific_patterns(text)
        
        # Clean up
        text = ' '.join(text.split())
        return text
    
    def _fix_punctuation_spacing(self, text: str) -> str:
        """Fix spacing around punctuation."""
        # Space after punctuation
        text = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', text)
        
        # Space after closing brackets/parentheses
        text = re.sub(r'([\)\]])([A-Za-z])', r'\1 \2', text)
        
        # Space before opening brackets/parentheses
        text = re.sub(r'([A-Za-z])([\(\[])', r'\1 \2', text)
        
        # Handle dashes - ensure spaces around them
        text = re.sub(r'—+', ' — ', text)
        text = re.sub(r'-{3,}', ' — ', text)
        
        # Fix period followed by number (but not decimals)
        text = re.sub(r'\.(\d)', lambda m: '. ' + m.group(1) 
                     if not text[max(0, m.start()-1)].isdigit() 
                     else m.group(0), text)
        
        return text
    
    def _fix_camel_case(self, text: str) -> str:
        """Intelligently split camelCase."""
        def replace_camel(match):
            word = match.group(0)
            # Don't split if it's a known word that should be preserved
            if word.lower() in self.preserve_words:
                return word
            
            # Add space before capital letter
            result = match.group(1) + ' ' + match.group(2)
            return result
        
        # Handle lowercase followed by uppercase
        text = re.sub(r'([a-z])([A-Z])', replace_camel, text)
        
        # Handle multiple capitals followed by lowercase (e.g., "USAToday" -> "USA Today")
        text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
        
        return text
    
    def _apply_patterns(self, text: str) -> str:
        """Apply all concatenation patterns."""
        for pattern, replacement in self.concat_patterns:
            if callable(replacement):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            else:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _fix_number_spacing(self, text: str) -> str:
        """Fix spacing around numbers."""
        # Units after numbers
        text = re.sub(r'(\d+\.?\d*)(mL|mg|mcg|IU|L)', r'\1 \2', text)
        
        # Years pattern
        text = re.sub(r'(\d{4})-(\d{4})', r'\1-\2', text)  # Keep year ranges together
        
        # Fix "Use2024" -> "Use 2024" but not "H1N1"
        def fix_text_number(match):
            prefix = match.group(1)
            number = match.group(2)
            
            # If it's a year (4 digits) and prefix is a regular word
            if len(number) == 4 and prefix.lower() in ['use', 'formula', 'approval', 'year']:
                return prefix + ' ' + number
            return match.group(0)
        
        text = re.sub(r'([A-Za-z]+)(\d+)', fix_text_number, text)
        
        # Fix patterns like "18years" -> "18 years"
        text = re.sub(r'(\d+)(years?|months?|days?|weeks?)', r'\1 \2', text)
        
        return text
    
    def _fix_specific_patterns(self, text: str) -> str:
        """Fix specific problematic patterns."""
        # Fix "Thesehighlights" type patterns
        text = re.sub(r'\bThesehighlights', 'These highlights', text, flags=re.IGNORECASE)
        
        # Fix "ahistory" -> "a history"
        text = re.sub(r'\b(a)(history|vaccine|single|severe)\b', r'\1 \2', text, flags=re.IGNORECASE)
        
        # Fix specific drug names
        text = re.sub(r'Flublok([a-z])', r'Flublok \1', text)
        
        # Fix approval patterns
        text = re.sub(r'U\.S\.([A-Z])', r'U.S. \1', text)
        
        # Fix concatenated small words
        small_words = ['a', 'an', 'the', 'of', 'to', 'for', 'in', 'on', 'at', 'by', 'is', 'it']
        for word in small_words:
            # Pattern: small word directly followed by capital letter
            pattern = rf'\b({word})([A-Z])'
            text = re.sub(pattern, rf'\1 \2', text, flags=re.IGNORECASE)
        
        return text


def fix_pharmaceutical_text_spacing(text: str) -> str:
    """Convenience function to fix spacing in pharmaceutical text."""
    fixer = SmartSpacingFixer()
    return fixer.fix_spacing(text)