# Text Processing Architecture

This module provides robust text processing capabilities for handling PDF-extracted text, including normalization and quote matching.

## Key Design Decision: Normalized Text Only

We use **normalized text throughout the entire pipeline**:

1. **Normalized text is the single source of truth**: 
   - Shown to the LLM for cleaner quote extraction
   - Used to verify quotes (simple string matching)
   - Used for position finding (no coordinate translation needed)

2. **Benefits of single text representation**:
   - No complex quote matching needed
   - 100% quote verification success (if LLM quotes it, we find it)
   - Simpler mental model and codebase
   - ~400 lines of code removed

## Philosophy: Hold LLM Accountable Only for What It Sees

Since the LLM only sees normalized text:
- We verify quotes against the same normalized text
- Position finding uses the same coordinate system
- Raw text is only accessed if needed for PDF export/highlighting

## Components

### TextNormalizer
Applies multiple normalization strategies:
- **WhitespaceNormalizer**: Normalizes spaces, tabs, newlines
- **PunctuationNormalizer**: Standardizes quotes, dashes
- **HyphenationNormalizer**: Removes line-break hyphenation
- **NumberNormalizer**: Normalizes number formats
- **LigatureNormalizer**: Expands PDF ligatures (ﬁ→fi, ﬂ→fl)
- **CaseNormalizer**: Converts to lowercase
- **UnicodeNormalizer**: Handles unicode variations

## Usage Flow

1. **Document Loading**:
   ```python
   interface = FactCheckInterface(document)
   normalized_text = interface.get_full_text(normalize=True)
   ```

2. **Evidence Extraction**:
   ```python
   result = await evidence_extractor.extract_supporting_evidence(
       claim=claim,
       document_text=normalized_text
   )
   ```

3. **Verification Process**:
   - LLM extracts quotes from normalized text
   - Verify quotes with simple `str.find()` (100% success rate)
   - Positions are already in normalized coordinate space
   - No complex matching or translation needed

## Benefits

1. **Better LLM Performance**: Clean text improves quote extraction
2. **Accurate Positioning**: Quotes found in original document
3. **Transparency**: Know how each quote was matched
4. **Configurable**: Adjust matching strictness as needed
5. **Handles PDF Artifacts**: Ligatures, hyphenation, spacing issues