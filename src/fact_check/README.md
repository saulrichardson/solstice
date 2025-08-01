# Fact Check Module

Advanced multi-agent system for automated fact-checking against processed documents.

## Architecture Overview

The fact_check module implements a sophisticated pipeline for verifying claims against document evidence using multiple specialized AI agents. It supports both text and visual evidence extraction, providing comprehensive fact-checking capabilities for clinical, scientific, and marketing documents.

### Core Design Principles

- **Multi-Agent Architecture**: Specialized agents handle different aspects of fact-checking
- **Evidence Pipeline**: Sequential processing with verification and completeness checks
- **Vision Integration**: Automatic analysis of tables, figures, and charts
- **Model Flexibility**: Configurable models per agent for optimal performance
- **Parallel Processing**: Efficient handling of multiple documents and images
- **Structured Output**: Standardized evidence format for downstream consumption

## Component Architecture

### 1. Agents (`agents/`)

The module uses specialized agents that inherit from `BaseAgent`:

#### **EvidenceExtractor**
- **Purpose**: Extracts exact quotes from documents that support claims
- **Inputs**: Document content JSON, claim text (from config)
- **Model**: Configurable (default: gpt-4.1)
- **Output**: `extracted_evidence` array containing quotes with relevance explanations

#### **CompletenessChecker**
- **Purpose**: Finds additional supporting quotes not caught in initial extraction
- **Inputs**: Document content JSON, evidence extractor output
- **Model**: Configurable (default: gpt-4.1)
- **Output**: `combined_evidence` array merging original + new quotes (duplicates removed)

#### **EvidenceVerifierV2**
- **Purpose**: Verifies quotes exist in the document and genuinely support the claim
- **Inputs**: Document content JSON, completeness checker output (`combined_evidence`)
- **Model**: Configurable (default: gpt-4.1)
- **Output**: `verified_evidence` and `rejected_evidence` arrays with verification results

#### **ImageEvidenceAnalyzer**
- **Purpose**: Analyzes visual content (tables, figures, charts) for evidence
- **Inputs**: Individual image file, image metadata (page, type), claim text
- **Model**: Vision-capable (default: o4-mini)
- **Output**: Per-image analysis with `supports_claim` boolean, reasoning, and evidence details
- **Features**: Parallel image processing, automatic figure discovery

#### **EvidencePresenter**
- **Purpose**: Consolidates all evidence into a structured presentation (non-LLM)
- **Type**: Formatting agent (no LLM calls)
- **Output**: Final evidence report with supporting_evidence and image_supporting_evidence arrays

### 2. Orchestrators (`orchestrators/`)

#### **ClaimOrchestrator**
- Processes single claims across multiple documents
- Coordinates agent pipeline execution
- Manages caching and result aggregation

#### **StudyOrchestrator**
- Handles batch processing of multiple claims
- Generates comprehensive study reports
- Provides progress tracking and error handling

### 3. Configuration (`config/`)

#### **agent_models.py**
```python
AGENT_MODELS = {
    "evidence_extractor": "gpt-4.1",
    "evidence_verifier_v2": "gpt-4.1",
    "completeness_checker": "gpt-4.1",
    "image_evidence_analyzer": "o4-mini",  # Vision-capable
    "evidence_presenter": "gpt-4.1",
    "default": "gpt-4.1"
}
```

#### **model_capabilities.py**
- Model feature detection (vision support, context limits)
- Automatic request adaptation
- Response parsing strategies

### 4. Models (`models/`)

#### **llm_outputs.py**
- Pydantic models for agent outputs
- Type-safe evidence structures
- Validation and serialization

#### **image_outputs.py**
- Image analysis result models
- Evidence classification for visual content

### 5. Core (`core/`)

#### **responses_client.py**
- Gateway client for LLM interactions
- Request formatting and response parsing
- Error handling and retries

### 6. Utils (`utils/`)

- **document_utils.py**: Document loading and preprocessing
- **json_parser.py**: Robust JSON extraction from LLM responses
- **llm_parser.py**: Model-specific response parsing
- **report_generator.py**: HTML/Markdown report generation

## Processing Pipeline

```
Claim Input
    │
    ├─► ClaimOrchestrator
    │       │
    │       ├─► Load Documents (parallel)
    │       │
    │       ├─► Text Evidence Pipeline
    │       │   ├─► EvidenceExtractor
    │       │   ├─► CompletenessChecker
    │       │   └─► EvidenceVerifierV2
    │       │
    │       ├─► Image Evidence Pipeline (parallel)
    │       │   └─► ImageEvidenceAnalyzer (per image)
    │       │
    │       └─► EvidencePresenter
    │               │
    │               └─► Structured Evidence Output
```

## Usage Examples

### CLI Integration

```bash
# Run fact-checking study with default settings
python -m src.cli run-study

# Check specific claims against specific documents
python -m src.cli run-study \
    --claims data/claims/Flublok_Claims.json \
    --documents FlublokPI FlublokQA

# Custom output directory
python -m src.cli run-study --output-dir results/
```

### Programmatic Usage

```python
from src.fact_check.orchestrators import ClaimOrchestrator

# Process single claim
orchestrator = ClaimOrchestrator(
    claim_id="claim_001",
    claim_text="Flublok is FDA approved for adults 18+",
    documents=["FlublokPI", "FlublokQA"],
    cache_dir=Path("data/scientific_cache")
)

results = await orchestrator.process()

# Access evidence
for doc_name, doc_result in results["documents"].items():
    print(f"Document: {doc_name}")
    print(f"Supporting: {doc_result['supporting_evidence']}")
    print(f"Image evidence: {doc_result.get('image_evidence', [])}")
    print(f"Coverage: {doc_result['evidence_summary']['coverage']}")
```

### Batch Processing

```python
from src.fact_check.orchestrators import StudyOrchestrator

study = StudyOrchestrator(
    claims_file="claims.json",
    documents=["doc1", "doc2"],
    output_dir=Path("results/")
)

await study.process()
# Generates comprehensive report with all claim-document pairs
```

## Output Format

### Evidence Structure

```json
{
  "claim_id": "claim_001",
  "claim": "...",
  "documents": {
    "FlublokPI": {
      "document": "FlublokPI",
      "supporting_evidence": [
        {
          "quote": "Exact quote from document",
          "explanation": "This quote directly states that Flublok is FDA approved for adults 18 years and older"
        }
      ],
      "image_evidence": [
        {
          "filename": "table_p1_abc123.png",
          "supports_claim": true,
          "reasoning": "Table shows age ranges including 18+"
        }
      ],
      "evidence_summary": {
        "coverage": "complete",
        "total_evidence": 5
      },
      "success": true
    }
  }
}
```

## Configuration

### Model Configuration

Models are configured in `config/agent_models.py`. To change models, edit the AGENT_MODELS dictionary in that file.

### Custom Agent Configuration

```python
config = {
    "agent_config": {
        "evidence_extractor": {
            "max_evidence_items": 10,
            "include_context": True
        },
        "image_analyzer": {
            "parallel_images": 5,
            "timeout_per_image": 30
        }
    },
    "models": {
        "evidence_extractor": "custom-model-v2"
    }
}
```

## Performance Optimization

### Caching Strategy
- Agent outputs cached per claim-document pair
- Intermediate results saved for debugging
- Cache invalidation on document updates

### Parallel Processing
- Documents processed concurrently
- Images analyzed in parallel batches
- Async I/O for gateway communication

### Resource Management
- Memory monitoring for large documents
- Automatic batch sizing
- Graceful degradation on resource constraints

## Integration Points

### With Ingestion Module
- Consumes extracted content.json from cache
- Reads extracted figures from cache directories
- Uses document metadata for context

### With Gateway Module
- All LLM calls routed through gateway
- Request/response logging
- Retry handling

### With CLI Module
- Integrated as `run-study` command
- Progress reporting
- Result formatting

## Best Practices

### Claim Writing
```python
# Good: Specific, verifiable claims
"Flublok is FDA approved for adults 18 years and older"

# Bad: Vague or compound claims  
"Flublok is good and safe"
```

### Document Preparation
1. Ensure documents are properly ingested
2. Verify figure extraction completed
3. Check document text quality

### Error Handling
```python
try:
    results = await orchestrator.process()
except AgentError as e:
    logger.error(f"Agent failed: {e}")
    # Handle gracefully
```

## Testing

```bash
# Run unit tests
pytest src/fact_check/tests/

# Test model capabilities
pytest src/fact_check/tests/test_model_capabilities.py

# Integration tests
pytest tests/integration/test_fact_check_pipeline.py
```

## Future Enhancements

1. **Multi-Modal Evidence**: Combined text-image evidence chains
2. **Confidence Scoring**: ML-based confidence models
3. **Citation Graphs**: Reference tracking and validation
4. **Claim Dependencies**: Understanding related claims
5. **Real-time Updates**: Streaming evidence as found
6. **Custom Agents**: Plugin architecture for domain-specific agents
7. **Evidence Ranking**: Relevance scoring for evidence
8. **Explanation Generation**: Natural language explanations