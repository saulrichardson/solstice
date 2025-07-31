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
- **Purpose**: Identifies relevant text passages that may support or contradict claims
- **Model**: Configurable (default: gpt-4.1)
- **Output**: List of potential evidence passages with locations

#### **EvidenceVerifierV2**
- **Purpose**: Verifies exact quotes and ensures evidence accuracy
- **Model**: Configurable (default: gpt-4.1)
- **Features**: Quote verification, context validation, source tracking

#### **CompletenessChecker**
- **Purpose**: Identifies gaps in evidence and suggests additional searches
- **Model**: Configurable (default: gpt-4.1)
- **Output**: Missing evidence types, suggested search areas

#### **ImageEvidenceAnalyzer**
- **Purpose**: Analyzes visual content (tables, figures, charts) for evidence
- **Model**: Vision-capable (default: o4-mini)
- **Features**: Parallel image processing, automatic figure discovery

#### **EvidencePresenter**
- **Purpose**: Consolidates all evidence into a structured presentation
- **Model**: Configurable (default: gpt-4.1)
- **Output**: Final evidence report with confidence levels

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
- **resource_monitor.py**: Performance tracking and optimization

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
    │       │   ├─► EvidenceVerifierV2
    │       │   └─► CompletenessChecker
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

results = orchestrator.process_claim()

# Access evidence
for doc_result in results["document_results"]:
    print(f"Document: {doc_result['document']}")
    print(f"Supporting: {doc_result['supporting_evidence']}")
    print(f"Images: {doc_result['image_supporting_evidence']}")
```

### Batch Processing

```python
from src.fact_check.orchestrators import StudyOrchestrator

study = StudyOrchestrator(
    claims_file="claims.json",
    documents=["doc1", "doc2"],
    output_dir=Path("results/")
)

study.run()
# Generates comprehensive report with all claim-document pairs
```

## Output Format

### Evidence Structure

```json
{
  "claim_id": "claim_001",
  "claim_text": "...",
  "document_results": [
    {
      "document": "FlublokPI",
      "supporting_evidence": [
        {
          "text": "Exact quote from document",
          "location": "Page 5, Section 2.1",
          "confidence": "high"
        }
      ],
      "contradicting_evidence": [],
      "image_supporting_evidence": [
        {
          "image_filename": "table_p1_abc123.png",
          "explanation": "Table shows age ranges including 18+",
          "confidence": "high"
        }
      ],
      "missing_evidence": {
        "clinical_trials": "No trial data found for age group"
      }
    }
  ]
}
```

## Configuration

### Environment Variables

```bash
# Model selection
FACT_CHECK_DEFAULT_MODEL=gpt-4.1
FACT_CHECK_VISION_MODEL=o4-mini

# Performance tuning
FACT_CHECK_MAX_WORKERS=10
FACT_CHECK_TIMEOUT=300

# Debugging
FACT_CHECK_LOG_LEVEL=INFO
FACT_CHECK_SAVE_INTERMEDIATE=true
```

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
- Agent outputs cached per claim-document pair in scientific_cache
- Intermediate results saved for debugging
- Scientific_cache invalidation on document updates

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
- Consumes `Document` objects from ingestion
- Reads extracted figures from scientific_cache
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
    results = orchestrator.process_claim()
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