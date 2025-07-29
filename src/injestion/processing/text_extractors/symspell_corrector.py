"""SymSpellPy-based text corrector for medical/pharmaceutical documents.

This provides a general spell-checking and compound-splitting solution
instead of endless pattern matching.
"""

import logging
import re
from pathlib import Path
from typing import List, Set, Optional
import pkg_resources

try:
    from symspellpy import SymSpell, Verbosity
    SYMSPELL_AVAILABLE = True
except ImportError:
    SYMSPELL_AVAILABLE = False
    SymSpell = None
    Verbosity = None

logger = logging.getLogger(__name__)


class SymSpellCorrector:
    """Text corrector using SymSpellPy for medical documents."""
    
    def __init__(self, 
                 dictionary_path: Optional[Path] = None,
                 max_edit_distance: int = 2,
                 prefix_length: int = 7):
        """Initialize SymSpell corrector.
        
        Args:
            dictionary_path: Path to frequency dictionary file
            max_edit_distance: Maximum edit distance for corrections
            prefix_length: Prefix length for internal data structure
        """
        if not SYMSPELL_AVAILABLE:
            raise ImportError("SymSpellPy is required. Install with: pip install symspellpy")
        
        self.sym_spell = SymSpell(max_edit_distance, prefix_length)
        self.max_edit_distance = max_edit_distance
        
        # Load dictionary
        if dictionary_path and dictionary_path.exists():
            self._load_dictionary(dictionary_path)
        else:
            self._load_default_dictionary()
        
        # Add medical terms
        self._add_medical_terms()
        
        # Terms that should never be split
        self.no_split_terms = {
            'flublok', 'covid', 'mrna', 'sars', 'igg', 'iga',
            'influenza', 'vaccine', 'intramuscular', 'hemagglutinin',
            'neuraminidase', 'adjuvant', 'quadrivalent', 'trivalent',
            'immunogenicity', 'reactogenicity', 'seroconversion',
            'seroprotection', 'hemagglutination', 'microneutralization'
        }
        
        # Common medical abbreviations
        self.medical_abbreviations = {
            'iiv', 'riv', 'laiv', 'ha', 'na', 'who', 'cdc', 'fda',
            'acip', 'vrbpac', 'gmp', 'ph', 'im', 'id', 'sc'
        }
        
    def _load_dictionary(self, dictionary_path: Path):
        """Load frequency dictionary from file."""
        if not self.sym_spell.load_dictionary(str(dictionary_path), 0, 1):
            logger.warning(f"Failed to load dictionary from {dictionary_path}")
            self._load_default_dictionary()
    
    def _load_default_dictionary(self):
        """Load default English frequency dictionary."""
        # Try to load built-in dictionary
        try:
            # SymSpellPy includes frequency dictionaries
            dict_path = pkg_resources.resource_filename(
                "symspellpy", "frequency_dictionary_en_82_765.txt"
            )
            if Path(dict_path).exists():
                self.sym_spell.load_dictionary(dict_path, 0, 1)
                logger.info("Loaded default English dictionary")
                return
        except:
            pass
        
        # Fallback: Create minimal dictionary
        logger.warning("No dictionary found, creating minimal dictionary")
        basic_words = [
            ("the", 1000000), ("of", 900000), ("and", 800000), ("to", 700000),
            ("in", 600000), ("a", 500000), ("is", 400000), ("for", 300000),
            ("with", 250000), ("or", 200000), ("by", 150000), ("from", 140000),
            ("be", 130000), ("are", 120000), ("been", 110000), ("have", 100000),
            ("their", 90000), ("has", 80000), ("had", 70000), ("were", 60000),
            ("will", 50000), ("would", 40000), ("could", 30000), ("should", 20000),
            ("may", 15000), ("might", 10000), ("must", 9000), ("shall", 8000),
            ("can", 7000), ("cannot", 6000), ("could", 5000), ("would", 4000),
            ("vaccine", 10000), ("vaccines", 9000), ("influenza", 8000),
            ("dose", 7000), ("doses", 6000), ("administration", 5000),
            ("injection", 4000), ("immunization", 3000), ("vaccination", 2000)
        ]
        
        for word, freq in basic_words:
            self.sym_spell.create_dictionary_entry(word, freq)
    
    def _add_medical_terms(self):
        """Add medical and pharmaceutical terms to dictionary."""
        medical_terms = [
            # Common medical terms
            "vaccine", "vaccines", "vaccination", "vaccinate", "vaccinated",
            "immunization", "immunize", "immunized", "immunity", "immune",
            "antibody", "antibodies", "antigen", "antigens", "antigenic",
            "virus", "viruses", "viral", "virologic", "virology",
            "influenza", "flu", "pandemic", "epidemic", "endemic",
            "strain", "strains", "subtype", "subtypes", "variant",
            "dose", "doses", "dosage", "dosing", "administration",
            "injection", "injections", "intramuscular", "subcutaneous",
            "contraindication", "contraindications", "contraindicated",
            "precaution", "precautions", "warning", "warnings",
            "adverse", "reaction", "reactions", "event", "events",
            "efficacy", "effectiveness", "safety", "tolerability",
            "clinical", "trial", "trials", "study", "studies",
            "placebo", "control", "controlled", "randomized",
            
            # Specific vaccine terms
            "hemagglutinin", "neuraminidase", "adjuvant", "adjuvanted",
            "inactivated", "attenuated", "recombinant", "quadrivalent",
            "trivalent", "monovalent", "bivalent", "polyvalent",
            
            # Immunology terms
            "immunogenicity", "immunogenic", "seroconversion", "seroprotection",
            "hemagglutination", "inhibition", "microneutralization",
            "lymphocyte", "lymphocytes", "cytokine", "cytokines",
            
            # Pharmaceutical terms
            "formulation", "formulated", "excipient", "excipients",
            "preservative", "stabilizer", "buffer", "buffered",
            "storage", "refrigerated", "frozen", "lyophilized",
            
            # Anatomy terms
            "respiratory", "pulmonary", "nasal", "pharyngeal",
            "muscle", "deltoid", "systemic", "local",
            
            # Age groups
            "pediatric", "adult", "adults", "geriatric", "elderly",
            "infant", "infants", "child", "children", "adolescent",
            
            # Organizations
            "cdc", "fda", "who", "acip", "vrbpac", "ema",
            
            # Units
            "ml", "mg", "mcg", "iu", "years", "months", "days",
            
            # Product names (add more as needed)
            "flublok", "fluzone", "fluarix", "flulaval", "flucelvax",
            "afluria", "flumist", "fluad"
        ]
        
        # Add each term with reasonable frequency
        for term in medical_terms:
            self.sym_spell.create_dictionary_entry(term.lower(), 1000)
    
    def correct_text(self, text: str) -> str:
        """Correct text using SymSpell.
        
        Args:
            text: Input text with potential errors
            
        Returns:
            Corrected text
        """
        if not text:
            return text
        
        # Step 1: Fix obvious ligatures
        text = self._fix_ligatures(text)
        
        # Step 2: Pre-process for common patterns
        text = self._preprocess_text(text)
        
        # Step 3: Split into lines to preserve structure
        lines = text.split('\n')
        corrected_lines = []
        
        for line in lines:
            if not line.strip():
                corrected_lines.append(line)
                continue
            
            # Process each line
            corrected_line = self._correct_line(line)
            corrected_lines.append(corrected_line)
        
        # Step 4: Post-process
        result = '\n'.join(corrected_lines)
        result = self._postprocess_text(result)
        
        return result
    
    def _fix_ligatures(self, text: str) -> str:
        """Fix common ligatures."""
        replacements = {
            'ﬂ': 'fl', 'ﬁ': 'fi', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl',
            'ﬅ': 'st', 'ﬆ': 'st', '№': 'No', '℠': 'SM', '™': 'TM', '®': '(R)'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def _preprocess_text(self, text: str) -> str:
        """Pre-process text before correction."""
        # Fix specific known issues
        text = text.replace('inﬂuenza', 'influenza')
        text = text.replace('INFL UENZA', 'INFLUENZA')
        
        # Fix units that are concatenated
        text = re.sub(r'(\d+\.?\d*)mL', r'\1 mL', text)
        text = re.sub(r'(\d+\.?\d*)mg', r'\1 mg', text)
        text = re.sub(r'(\d+\.?\d*)mcg', r'\1 mcg', text)
        
        # Fix years
        text = re.sub(r'(\d+)years', r'\1 years', text)
        text = re.sub(r'(\d+)months', r'\1 months', text)
        
        return text
    
    def _correct_line(self, line: str) -> str:
        """Correct a single line of text."""
        # Handle different types of content
        
        # If it's a header (all caps or mostly caps), be conservative
        if self._is_header(line):
            return self._correct_header(line)
        
        # For regular text, do full correction
        words = line.split()
        corrected_words = []
        
        i = 0
        while i < len(words):
            word = words[i]
            
            # Extract punctuation
            word_clean, prefix, suffix = self._extract_punctuation(word)
            
            if not word_clean:
                corrected_words.append(word)
                i += 1
                continue
            
            # Check if it's a special term
            if self._is_special_term(word_clean):
                corrected_words.append(prefix + word_clean + suffix)
                i += 1
                continue
            
            # Try to correct the word
            corrected = self._correct_word(word_clean)
            
            # Handle compound words
            if corrected == word_clean and len(word_clean) > 10:
                # Try compound splitting
                split_result = self._split_compound(word_clean)
                if split_result != word_clean:
                    corrected = split_result
            
            corrected_words.append(prefix + corrected + suffix)
            i += 1
        
        return ' '.join(corrected_words)
    
    def _is_header(self, line: str) -> bool:
        """Check if line is likely a header."""
        if not line.strip():
            return False
        
        # Count uppercase letters
        upper_count = sum(1 for c in line if c.isupper())
        total_letters = sum(1 for c in line if c.isalpha())
        
        if total_letters == 0:
            return False
        
        # If more than 70% uppercase, it's likely a header
        return (upper_count / total_letters) > 0.7
    
    def _correct_header(self, line: str) -> str:
        """Correct header text (conservative approach)."""
        # Only fix very obvious issues in headers
        corrections = {
            'UBLOK': 'FLUBLOK',
            'NFORMATION': 'INFORMATION',
            'DMINISTRATION': 'ADMINISTRATION',
            'ONTRAINDICATIONS': 'CONTRAINDICATIONS',
            'RECAUTIONS': 'PRECAUTIONS',
            'EACTIONS': 'REACTIONS',
            'NTERACTIONS': 'INTERACTIONS'
        }
        
        for old, new in corrections.items():
            line = re.sub(r'\b' + old + r'\b', new, line)
        
        return line
    
    def _extract_punctuation(self, word: str) -> tuple:
        """Extract leading and trailing punctuation."""
        prefix = ''
        suffix = ''
        
        # Extract leading punctuation
        while word and not word[0].isalnum():
            prefix += word[0]
            word = word[1:]
        
        # Extract trailing punctuation (but keep ® and ™)
        while word and word[-1] in '.,;:!?\'"':
            suffix = word[-1] + suffix
            word = word[:-1]
        
        return word, prefix, suffix
    
    def _is_special_term(self, word: str) -> bool:
        """Check if word is a special term that shouldn't be corrected."""
        word_lower = word.lower()
        
        # Don't correct abbreviations
        if word.isupper() and len(word) <= 5:
            return True
        
        # Don't correct known medical abbreviations
        if word_lower in self.medical_abbreviations:
            return True
        
        # Don't correct numbers or codes
        if any(c.isdigit() for c in word):
            return True
        
        # Don't correct terms with special characters
        if any(c in word for c in ['®', '™', '-', '/']):
            return True
        
        return False
    
    def _correct_word(self, word: str) -> str:
        """Correct a single word."""
        # First check if it's already correct
        if self.sym_spell.lookup(word, Verbosity.TOP, max_edit_distance=0):
            return word
        
        # Try different case variations
        suggestions = []
        
        # Try exact case
        result = self.sym_spell.lookup(word, Verbosity.TOP, max_edit_distance=self.max_edit_distance)
        if result:
            suggestions.extend([(s.term, s.distance) for s in result])
        
        # Try lowercase
        if word != word.lower():
            result = self.sym_spell.lookup(word.lower(), Verbosity.TOP, max_edit_distance=self.max_edit_distance)
            if result:
                # Restore original case pattern
                for s in result:
                    restored = self._restore_case(word, s.term)
                    suggestions.append((restored, s.distance))
        
        if not suggestions:
            return word
        
        # Sort by edit distance
        suggestions.sort(key=lambda x: x[1])
        
        # Return the best suggestion
        return suggestions[0][0]
    
    def _split_compound(self, word: str) -> str:
        """Try to split compound word."""
        # Skip if it's a known no-split term
        if word.lower() in self.no_split_terms:
            return word
        
        # Try word segmentation
        result = self.sym_spell.word_segmentation(word.lower(), max_edit_distance=0)
        
        if result.corrected_string != word.lower() and ' ' in result.corrected_string:
            # Split was successful
            parts = result.corrected_string.split()
            
            # Validate the split
            if self._validate_split(parts):
                # Restore case
                return self._restore_compound_case(word, parts)
        
        return word
    
    def _validate_split(self, parts: List[str]) -> bool:
        """Validate that a split is reasonable."""
        # Don't accept too many tiny parts
        if len(parts) > 5:
            return False
        
        # Check each part
        for part in parts:
            # Accept common short words
            if part in {'a', 'i', 'of', 'to', 'in', 'is', 'it', 'be', 'as', 'at', 'by', 'or', 'an', 'the', 'and', 'for'}:
                continue
            
            # Reject single letters (except a, i)
            if len(part) == 1:
                return False
            
            # Reject very short unknown words
            if len(part) == 2 and not self.sym_spell.lookup(part, Verbosity.TOP, max_edit_distance=0):
                return False
        
        return True
    
    def _restore_case(self, original: str, corrected: str) -> str:
        """Restore the case pattern from original to corrected word."""
        if original.isupper():
            return corrected.upper()
        elif original[0].isupper():
            return corrected.capitalize()
        else:
            return corrected
    
    def _restore_compound_case(self, original: str, parts: List[str]) -> str:
        """Restore case for compound word parts."""
        if original.isupper():
            # For all caps, keep articles lowercase
            keep_lower = {'of', 'and', 'the', 'to', 'for', 'in', 'a', 'an'}
            return ' '.join(p.upper() if p not in keep_lower else p for p in parts)
        elif original[0].isupper():
            # Capitalize first word
            parts[0] = parts[0].capitalize()
            return ' '.join(parts)
        else:
            return ' '.join(parts)
    
    def _postprocess_text(self, text: str) -> str:
        """Post-process corrected text."""
        # Fix any double spaces
        text = re.sub(r' +', ' ', text)
        
        # Fix spacing around punctuation
        text = re.sub(r' ([.,;:!?])', r'\1', text)
        
        # Fix specific patterns that SymSpell might miss
        patterns = [
            (r'isthe\b', 'is the'),
            (r'ofthe\b', 'of the'),
            (r'tothe\b', 'to the'),
            (r'inthe\b', 'in the'),
            (r'forthe\b', 'for the'),
            (r'andthe\b', 'and the'),
            (r'fromthe\b', 'from the'),
            (r'withthe\b', 'with the'),
            (r'oneor\b', 'one or'),
            (r'twoor\b', 'two or'),
            (r'threeor\b', 'three or'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Ensure single space after sentence endings
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        return text


def correct_medical_text(text: str, dictionary_path: Optional[Path] = None) -> str:
    """
    Correct medical text using SymSpell.
    
    This is the main entry point for spell-checking and compound splitting.
    
    Args:
        text: Text to correct
        dictionary_path: Optional path to custom dictionary
        
    Returns:
        Corrected text
    """
    if not SYMSPELL_AVAILABLE:
        logger.warning("SymSpellPy not available. Install with: pip install symspellpy")
        return text
    
    try:
        corrector = SymSpellCorrector(dictionary_path)
        return corrector.correct_text(text)
    except Exception as e:
        logger.error(f"Error in SymSpell correction: {e}")
        return text