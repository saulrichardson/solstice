# Vision Pipeline Documentation

## Overview

The vision pipeline is fully integrated into the fact-checking system, allowing automated analysis of images (tables, figures, charts) to find supporting evidence for claims.

## Architecture

### Modular Design

All components follow a single operating model:

1. **Base Agent Pattern**: All agents inherit from `BaseAgent`
   - `EvidenceExtractor` - Extracts text evidence
   - `EvidenceVerifierV2` - Verifies text quotes
   - `CompletenessChecker` - Checks for missing evidence
   - `ImageEvidenceAnalyzer` - Analyzes images for evidence
   - `EvidencePresenter` - Consolidates all evidence

2. **Model Capabilities System** (`config/model_capabilities.py`)
   - Centralized model configuration
   - Automatic request adaptation based on model
   - Model-specific response parsing

3. **Unified Pipeline Flow**:
   ```
   Text Pipeline:
   EvidenceExtractor → EvidenceVerifierV2 → CompletenessChecker → EvidencePresenter
                                                                         ↑
   Image Pipeline:                                                       |
   ImageEvidenceAnalyzer (parallel for all images) ────────────────────┘
   ```

## CLI Integration

The vision pipeline runs automatically as part of the standard fact-checking workflow:

```bash
python -m src.cli.run_study --documents FlublokPI --claims data/claims/Flublok_Claims.json
```

### What Happens:

1. For each claim-document pair:
   - Text evidence is extracted and verified
   - All images in `data/cache/{document}/extracted/figures/` are analyzed in parallel
   - Results are consolidated by the EvidencePresenter

2. Output includes both text and image evidence:
   ```json
   {
     "supporting_evidence": [...],  // Text evidence
     "image_supporting_evidence": [  // Image evidence
       {
         "image_filename": "table_p1_f8743488.png",
         "explanation": "The image shows..."
       }
     ]
   }
   ```

## Model Configuration

Models are configured in `config/agent_models.py`:

```python
AGENT_MODELS = {
    "evidence_extractor": "gpt-4.1",
    "evidence_verifier_v2": "gpt-4.1", 
    "completeness_checker": "gpt-4.1",
    "image_evidence_analyzer": "o4-mini",  # Vision-capable
    "default": "gpt-4.1"
}
```

## Image Analysis Process

1. **Discovery**: Finds all `.png` and `.jpg` files in the figures directory
2. **Parallel Analysis**: Analyzes all images concurrently using asyncio
3. **Evidence Filtering**: Only includes images that support the claim
4. **Result Integration**: Merges with text evidence in final presentation

## Logging

The image analyzer logs its activities:
```
INFO - Analyzing image table_p1_f8743488.png for claim claim_000
INFO - Result: Supports claim
```

## Key Features

- **Fully Modular**: Easy to extend or modify components
- **Model Agnostic**: Works with any vision-capable model
- **Parallel Processing**: Efficient image analysis
- **Unified Output**: Seamless integration of text and image evidence
- **No Orphaned Code**: Clean, maintainable structure

## Usage Example

To analyze all claims against all documents (text + images):

```bash
# Default: all documents with extracted content
python -m src.cli.run_study

# Specific document
python -m src.cli.run_study --documents FlublokPI

# Custom claims file
python -m src.cli.run_study --claims my_claims.json
```

The results will include both text and image evidence automatically.