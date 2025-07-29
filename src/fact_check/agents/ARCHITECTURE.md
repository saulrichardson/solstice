# Streamlined Fact-Checking Architecture

## Overview
Simplified pipeline focused on finding and presenting supporting evidence without judgments.

## Pipeline Flow

```
Claim + Document
      ↓
[1. Evidence Extractor]
      ↓
[2. Evidence Verifier]  ← Checks both existence AND applicability
      ↓
[3. Completeness Checker]
      ↓
[4. Evidence Presenter]
      ↓
Supporting Evidence
```

## Agent Specifications

### 1. Evidence Extractor
**Purpose**: Extract relevant quotes from documents

**Input**:
- `claim`: The claim to find evidence for
- `document`: Document JSON

**Output**:
```json
{
  "claim": "...",
  "extracted_evidence": [
    {
      "id": 1,
      "quote": "exact text from document",
      "relevance_explanation": "why this relates to the claim"
    }
  ]
}
```

---

### 2. Evidence Verifier
**Purpose**: Verify quotes exist AND actually support the claim in context

**Input**:
- Extracted evidence
- Original document

**Output**:
```json
{
  "verified_evidence": [
    {
      "id": 1,
      "quote": "...",
      "exists": true,
      "supports_claim": "yes",  // yes/no/partial
      "context_issues": [],
      "explanation": "This directly states what the claim asserts"
    }
  ],
  "rejected_evidence": [
    {
      "id": 2,
      "quote": "...",
      "reason": "Taken out of context - actually refers to different vaccine"
    }
  ]
}
```

**Key Features**:
- Single LLM call per quote that checks both existence and applicability
- Provides reasoning for keeping or rejecting each quote
- No arbitrary scores or classifications

---

### 3. Completeness Checker
**Purpose**: Identify gaps in evidence coverage

**Input**:
- Verified evidence
- Original document

**Output**:
```json
{
  "evidence_coverage": {
    "claim_aspects": ["aspect1", "aspect2"],
    "covered_aspects": ["aspect1"],
    "missing_aspects": ["aspect2"],
    "additional_evidence_found": [
      {
        "quote": "...",
        "addresses": "aspect2"
      }
    ]
  }
}
```

**Note**: Any additional evidence found goes back through Evidence Verifier

---

### 4. Evidence Presenter
**Purpose**: Format and present all supporting evidence

**Input**:
- All verified evidence
- Completeness assessment

**Output**:
```json
{
  "claim": "...",
  "supporting_evidence": [
    {
      "quote": "...",
      "explanation": "...",
      "strength": "strong"  // Optional metadata
    }
  ],
  "evidence_summary": {
    "total_found": 5,
    "coverage": "partial",
    "missing_aspects": ["standard dose comparison"]
  }
}
```

---

## Key Improvements

1. **Simplified Flow**: 4 agents instead of 5+
2. **Combined Verification**: One agent handles both existence and relevance
3. **No Judgments**: Just present evidence and coverage
4. **Clear Purpose**: Find supporting evidence, not judge claims
5. **Efficient**: Fewer LLM calls, clearer responsibilities

## Implementation Notes

- Evidence Verifier should use chunked context to verify quotes
- Completeness Checker can optionally search for missing evidence
- Evidence Presenter is purely formatting, no LLM calls needed
- All agents should handle batch processing efficiently