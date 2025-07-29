#!/usr/bin/env python3
"""Debug the spacing fixer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.injestion.processing.text_extractors.final_spacing_fixer import FinalSpacingFixer

# Test word
test = "theinformationneededtouseFlublok®safely"
print(f"Testing: {test}")

fixer = FinalSpacingFixer()

# Extract punctuation
clean, prefix, suffix = fixer._extract_punctuation(test)
print(f"Clean word: '{clean}', prefix: '{prefix}', suffix: '{suffix}'")

# Check if should split
should_split = fixer._should_split(clean)
print(f"Should split: {should_split}")

if should_split:
    # Try splitting
    split = fixer._split_word(clean)
    print(f"Split result: {split}")
else:
    print("Not splitting - why?")
    print(f"  Length > 5: {len(clean) > 5}")
    print(f"  Is digit: {clean.isdigit()}")
    print(f"  In preserve words: {clean.lower() in fixer.preserve_words}")
    
# Test full fix
fixed = fixer.fix_spacing(f"includeall {test}")
print(f"\nFull test: 'includeall {test}'")
print(f"Fixed: '{fixed}'")