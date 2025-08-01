# Fact Check Module

Verifies claims against document evidence using a pipeline of LLM agents.

## Core Workflow

1. **Extract** - Find quotes that might support the claim
2. **Complete** - Search for any missed quotes
3. **Verify** - Check quotes exist and actually support the claim
4. **Analyze Images** - Check figures/tables for supporting evidence
5. **Present** - Format verified evidence into final output

## Main Components

### Agents
- `EvidenceExtractor` - Finds initial quotes
- `CompletenessChecker` - Finds additional quotes
- `EvidenceVerifierV2` - Validates quotes
- `ImageEvidenceAnalyzer` - Analyzes figures/tables
- `EvidencePresenter` - Formats final output (non-LLM)

### Orchestrators
- `ClaimOrchestrator` - Runs agents for one claim across documents
- `StudyOrchestrator` - Processes multiple claims in batch

## Usage

```bash
# Run fact-checking study
python -m src.cli run-study
```

## Output

Results saved to `data/studies/` as:
- `study_results_*.json` - Detailed processing data
- `consolidated_results.json` - Clean evidence summary