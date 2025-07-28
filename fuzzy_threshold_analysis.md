# Fuzzy Matching Threshold Analysis for PDF Extraction Issues

## Current Implementation
- Default threshold: 0.90 (90%)
- Space-only differences: 0.92 (92%) - hardcoded special case

## Common PDF Extraction Issues Found

### 1. Missing Spaces
- Example: "HAproteins" vs "HA proteins"
- Current handling: Special case returns 92% match
- **Status: WORKING**

### 2. Missing Letters/Characters
- Example: "olyhedrosis" vs "polyhedrosis" (missing 'p')
- Example: "yringes" vs "syringes" (missing 's')
- Example: "olumn" vs "column" (missing 'c')
- Similarity: ~85-88%
- **Status: FAILING at 90% threshold**

### 3. Truncated Quotes with Ellipsis
- LLM adds "..." to indicate continuation
- Example: "Flublok [Influenza Vaccine] is a sterile, clear, c..."
- This is a partial match problem, not a fuzzy match problem
- **Status: FAILING - needs different solution**

## Recommendations

### 1. Lower the Threshold
Change from 0.90 to **0.85** to catch missing letter issues:
```python
def _fuzzy_find_quote(self, quote: str, text: str, threshold: float = 0.85):
```

### 2. Handle Truncated Quotes
Add logic to detect and handle ellipsis:
```python
# If quote ends with "...", search for the beginning part only
if quote.endswith("..."):
    quote_prefix = quote[:-3].rstrip()
    # Search for exact prefix match
    position = document_text.find(quote_prefix)
    if position != -1:
        # Extract full sentence/paragraph from that position
        # Return as verified with full text
```

### 3. Improve PDF Text Extraction
Consider pre-processing the extracted text to fix common OCR issues:
- Add missing spaces between CamelCase words
- Fix common OCR substitutions (0/O, 1/l/I, etc.)

### 4. Add Confidence Scoring
Instead of binary pass/fail, return confidence scores:
- 95-100%: Exact match
- 92-94%: Space-only differences  
- 85-91%: Minor character differences (likely OCR issues)
- Below 85%: Likely not a match

This would allow downstream processing to make informed decisions based on match quality.