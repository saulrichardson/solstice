# Fact-Check Pipeline Documentation

## Overview

The fact-check pipeline is an agent-based system designed to verify claims against extracted PDF documents. It builds on top of the ingestion pipeline output and provides a modular, extensible architecture for claim verification.

## Architecture

### Core Components

1. **Pipeline Orchestrator** (`pipeline.py`)
   - Manages agent lifecycle
   - Tracks pipeline state and progress
   - Handles error recovery and continuation
   - Saves results and manifests

2. **Base Agent** (`agents/base.py`)
   - Abstract base class for all agents
   - Provides I/O helpers and metadata management
   - Enforces consistent agent interface

3. **Text Evidence Finder** (`agents/text_evidence_finder.py`)
   - Verifies claims against document text
   - Uses LLM to analyze claims and find supporting/contradicting evidence
   - Extracts quotes and reasoning steps

4. **Responses Client** (`core/responses_client.py`)
   - Communicates with Solstice Gateway
   - Handles LLM API calls
   - No hardcoded URLs - uses environment configuration

## Usage

### Basic Command

```bash
python -m src.fact_check <pdf_name> <config_file>
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

## Verification Results Format

Each claim verification produces:
```json
{
  "claim": "Original claim text",
  "verdict": "supports|contradicts|insufficient",
  "confidence": 0.0-1.0,
  "success": true|false,
  "reasoning_steps": [
    {
      "id": 1,
      "reasoning": "Explanation of finding",
      "quote": "Exact quote from document",
      "start": 1234,  // Character position
      "end": 5678
    }
  ],
  "error": "Error message if failed"
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

1. **"Gateway URL must be provided"**
   - Set `SOLSTICE_GATEWAY_URL` environment variable
   - Or provide `gateway_url` in agent config

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