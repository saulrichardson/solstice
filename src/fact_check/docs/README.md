# Fact-Check Documentation

## Overview

The fact-check system is an agent-based architecture designed to extract supporting evidence for claims from clinical documents. It processes claims across multiple documents using a modular pipeline of specialized agents.

## Architecture

### Core Components

1. **Study Orchestrator** (`orchestrators/study_orchestrator.py`)
   - Processes all claims across all documents
   - Manages high-level workflow
   - Saves consolidated results

2. **Claim Orchestrator** (`orchestrators/claim_orchestrator.py`)
   - Processes one claim across all documents
   - Manages agent pipeline execution
   - Handles caching and error recovery

3. **Base Agent** (`agents/base.py`)
   - Abstract base class for all agents
   - Provides I/O helpers and metadata management
   - Enforces consistent agent interface

4. **Agent Pipeline**
   - **SupportingEvidenceExtractor**: Extracts text snippets that support claims
   - **RegexVerifier**: Verifies quotes exist in the document
   - **EvidenceCritic**: Critiques evidence quality (stub)
   - **EvidenceJudge**: Makes final judgment (stub)

5. **Responses Client** (`core/responses_client.py`)
   - Communicates with Solstice Gateway
   - Handles LLM API calls
   - No hardcoded URLs - uses environment configuration

## Usage

### Basic Command

```bash
# Run with all defaults (Flublok claims, all documents)
python -m src.cli run-study

# Run specific agents only
python -m src.cli run-study --agents supporting_evidence regex_verifier

# Run on specific documents
python -m src.cli run-study --documents FlublokPI "Liu et al. (2024)"
```

### Configuration Options

#### 1. Standalone Claims
```json
{
  "agents": {
    "text_evidence_finder": {
      "model": "gpt-4.1",
      "standalone_claims": [
        "Claim 1",
        "Claim 2"
      ]
    }
  }
}
```

#### 2. Claims from File
```json
{
  "agents": {
    "text_evidence_finder": {
      "model": "gpt-4.1",
      "claims_file": "Flublok_Claims.json"
    }
  }
}
```

Claims files should be placed in `data/claims/` and follow this format:
```json
{
  "claims": [
    {"claim": "Claim text 1"},
    {"claim": "Claim text 2"}
  ]
}
```

#### 3. Future: Claims from Claim Extractor
```json
{
  "agents": {
    "claim_extractor": {
      "model": "gpt-4.1"
    },
    "text_evidence_finder": {
      "model": "gpt-4.1"
    }
  }
}
```

### Environment Setup

```bash
# Required: Gateway URL
export SOLSTICE_GATEWAY_URL=http://localhost:8000

# Optional: OpenAI API key (if gateway requires it)
export OPENAI_API_KEY=your-key-here
```

## Output Structure

```
data/cache/<PDF_NAME>/agents/
├── pipeline_manifest.json       # Pipeline metadata and status
├── pipeline_results.json        # Combined results from all agents
└── text_evidence_finder/
    ├── metadata.json           # Agent run metadata
    ├── output.json             # Raw agent output
    ├── verification_results.json # Detailed claim verification
    └── summary.json            # Summary statistics
```

## Adding New Agents

1. Create a new file in `agents/` directory
2. Inherit from `BaseAgent`
3. Implement required methods:
   - `agent_name()`: Return unique agent identifier
   - `required_inputs()`: List required input files
   - `process()`: Main processing logic

Example:
```python
from typing import List, Dict, Any
from .base import BaseAgent

class MyNewAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "my_new_agent"
    
    @property
    def required_inputs(self) -> List[str]:
        return ["extracted/content.json"]
    
    async def process(self) -> Dict[str, Any]:
        # Your processing logic here
        return {"results": "..."}
```

4. Register in `pipeline.py`:
```python
from .agents.my_new_agent import MyNewAgent

# In _initialize_agents():
if "my_new_agent" in agent_configs:
    self.register_agent(MyNewAgent(...))
```

## Output Format

### Supporting Evidence Extractor
```json
{
  "claim_id": "claim_001",
  "claim": "Original claim text",
  "document": {
    "pdf_name": "FlublokPI",
    "source_pdf": "FlublokPI.pdf"
  },
  "extraction_result": {
    "success": true,
    "total_snippets_found": 3
  },
  "supporting_snippets": [
    {
      "id": 1,
      "quote": "Exact quote from document",
      "relevance_explanation": "Why this supports the claim",
      "location": {
        "start": 1234,
        "end": 5678,
        "page_number": 1
      }
    }
  ]
}
```

### Study Results
```json
{
  "metadata": {
    "claims_file": "data/claims/Flublok_Claims.json",
    "documents": ["FlublokPI", "Liu et al. (2024)"],
    "total_claims": 10
  },
  "claims": {
    "claim_001": {
      "claim": "Flublok is a recombinant vaccine",
      "documents": {
        "FlublokPI": { /* agent results */ }
      }
    }
  }
}
```

## Future Enhancements

1. **Visual Evidence Finder**: Analyze figures and tables for claim verification
2. **Claim Extractor**: Automatically extract claims from documents
3. **Cross-Document Verifier**: Compare claims across multiple sources
4. **Result Aggregator**: Combine evidence from multiple agents
5. **Report Generator**: Create human-readable verification reports

## Troubleshooting

### Common Issues

1. **Connection errors to gateway**
- Ensure the gateway is running locally (default at http://localhost:8000)
- To override, set the `SOLSTICE_GATEWAY_URL` environment variable or provide `gateway_url` in agent config

2. **"Input validation failed"**
   - Ensure required input files exist
   - Check PDF has been processed by ingestion pipeline

3. **"Quote not found"**
   - Known issue with character encoding
   - Quotes may contain ligatures or special characters
   - Fix in progress for quote normalization

### Debug Mode

Run with Python logging:
```bash
PYTHONPATH=. python -m src.fact_check FlublokPI config.json
```

Check logs for detailed error messages and LLM responses.
