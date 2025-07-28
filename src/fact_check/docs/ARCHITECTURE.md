# Fact-Check Architecture

## Overview

The fact-checking system uses a modular agent-based architecture with clear separation of concerns:

```
Study → Claims → Documents → Agents → Results
```

## Core Components

### 1. Agents (Lowest Level)
Individual agents that perform specific tasks:

- **SupportingEvidenceExtractor**: Extracts text snippets that support a claim
- **RegexVerifier**: Verifies quotes exist in the document
- **EvidenceCritic**: Critiques evidence quality and relevance
- **EvidenceJudge**: Makes final judgment based on all evidence

Each agent:
- Inherits from `BaseAgent`
- Processes one claim for one document
- Reads previous agent's output
- Saves results to standardized location

### 2. Orchestrators (Coordination)

#### ClaimOrchestrator
- Processes ONE claim across ALL documents
- Runs the agent pipeline for each document
- Manages agent sequencing and error handling

#### StudyOrchestrator  
- Processes ALL claims across ALL documents
- Uses ClaimOrchestrator for each claim
- Generates aggregate results

### 3. Data Flow

For each claim-document pair:
```
Document Text
    ↓
SupportingEvidenceExtractor
    ↓ (extracted snippets)
RegexVerifier
    ↓ (verified snippets)
EvidenceCritic
    ↓ (quality scores)
EvidenceJudge
    ↓ (final judgment)
Result
```

### 4. Storage Structure

```
data/cache/<DOCUMENT>/agents/claims/<CLAIM_ID>/
├── supporting_evidence/
│   └── output.json
├── regex_verifier/
│   └── output.json
├── evidence_critic/
│   └── output.json
└── evidence_judge/
    └── output.json
```

## Usage

### CLI Commands

```bash
# Run full study (recommended)
python -m src.cli run-study

# With options
python -m src.cli run-study \
    --claims data/claims/MyClaims.json \
    --documents Doc1 Doc2 Doc3 \
    --model gpt-4.1
```

### Python API

```python
from src.fact_check.orchestrators import StudyOrchestrator

# Create orchestrator
study = StudyOrchestrator(
    claims_file="data/claims/Flublok_Claims.json",
    documents=["FlublokPI", "Liu et al. (2024)"],
    config={"agent_config": {"model": "gpt-4.1"}}
)

# Run study
results = await study.run()

# Save results
study.save_results("results/my_study.json")
```

## Adding New Agents

1. Create agent class inheriting from `BaseAgent`
2. Implement required properties and methods
3. Add to agent sequence in `ClaimOrchestrator`
4. Update `agents/__init__.py`

Example:
```python
class MyNewAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "my_agent"
    
    @property
    def required_inputs(self) -> List[str]:
        return [f"agents/claims/{self.claim_id}/previous_agent/output.json"]
    
    async def process(self) -> Dict[str, Any]:
        # Your processing logic
        return {"results": "..."}
```

## Configuration

Agent behavior can be configured via the `agent_config` parameter:

```json
{
  "agent_config": {
    "model": "gpt-4.1",
    "temperature": 0.0,
    "custom_param": "value"
  },
  "continue_on_error": true
}
```

## Key Design Principles

1. **Single Responsibility**: Each agent does one thing well
2. **Sequential Processing**: Agents build on previous outputs
3. **Claim-Centric**: Process one claim fully before moving to next
4. **Cacheable**: Results stored on disk for reuse
5. **Extensible**: Easy to add new agents or modify pipeline