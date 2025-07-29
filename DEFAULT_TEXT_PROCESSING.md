# Default Text Processing Pipeline

## Overview

As of this update, **both SymSpell and WordNinja are enabled by default** in the text processing pipeline. This provides comprehensive text correction without requiring manual configuration.

## Default Pipeline Order

1. **Post-extraction cleaner** - Fixes PDF extraction artifacts
   - Truncated words (UBLOK → FLUBLOK)
   - Missing spaces after punctuation
   - Gibberish removal
   - Ligature replacement (ﬂ → fl)

2. **SymSpell** (NEW - enabled by default)
   - General spell-checking
   - Compound word splitting
   - Medical term recognition
   - Pattern-based pre-filtering for speed

3. **WordNinja** (via spacing_fix)
   - Specialized concatenated word splitting
   - Handles remaining concatenations
   - No dictionary required

## Performance Impact

With both enabled:
- Processing speed: ~90,000-140,000 chars/sec
- Accuracy: Significantly improved
- Memory: +5-10MB for SymSpell dictionary

## Configuration

### Default (both enabled):
```bash
python -m src.cli.ingest document.pdf
```

### To disable SymSpell only:
```bash
export USE_SYMSPELL=false
python -m src.cli.ingest document.pdf
```

## Example Processing

Input:
```
Thesehighlightsdonot include all theinformationneeded about inﬂuenzavirusstrains.
```

Output with both enabled:
```
These highlights do not include all the information needed about influenza virus strains.
```

## Benefits of Both

1. **Comprehensive coverage**: SymSpell handles misspellings and known patterns, WordNinja catches edge cases
2. **Better accuracy**: Two-stage approach catches more issues
3. **Flexibility**: Can disable SymSpell if speed is critical
4. **No configuration needed**: Works out of the box

## When to Disable SymSpell

Only disable SymSpell (USE_SYMSPELL=false) when:
- Processing extremely large volumes
- Microsecond latency is critical
- Documents have minimal spelling/spacing issues
- Memory is severely constrained

For typical usage, keep both enabled for best results.