# Fact Check Text Normalization Cleanup

## Summary

Removed duplicate text normalization from the fact_check module since the ingestion pipeline already handles comprehensive text normalization.

## Changes Made

### 1. **regex_verifier.py** - Removed duplicate normalization
- **Before**: Full whitespace normalization, punctuation spacing, quote normalization
- **After**: Only quote variation handling (smart quotes → regular quotes)
- **Reason**: Ingestion already handles whitespace and punctuation normalization

### 2. **document_utils.py** - Removed redundant strip() calls
- Removed `.strip()` from `block['text'].strip()` 
- Removed `.strip()` from final text assembly
- Updated docstrings to note text is pre-normalized
- **Reason**: Ingestion's post_extraction_cleaner already strips text

## What Was NOT Changed

### Kept these strip() operations:
1. **evidence_critic.py** - Parsing LLM responses
2. **completeness_checker.py** - Parsing LLM responses  
3. **evidence_extractor.py** - Parsing JSON/LLM responses
4. **supporting_evidence_extractor.py** - Uses document_utils (already fixed)

These are NOT normalizing document text - they're parsing API responses.

## Contract Clarification

### Ingestion Pipeline Guarantees:
- Whitespace normalized (no multiple spaces)
- Punctuation spacing fixed
- Leading/trailing whitespace removed
- Ligatures fixed (ﬂ → fl)
- Medical terms and units properly spaced

### Fact Check Module Responsibilities:
- Work with pre-normalized text from ingestion
- Only handle quote variations for better matching
- No duplicate normalization of document content

## Benefits

1. **Clear separation of concerns** - Ingestion normalizes, fact_check uses
2. **No duplicate processing** - Better performance
3. **Consistent text** - Single source of truth for normalization
4. **Maintainable** - Changes to normalization only needed in one place