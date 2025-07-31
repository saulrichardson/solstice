# Solstice – Clinical Document Fact-Checking Pipeline

Solstice verifies medical claims against clinical documents using computer vision and multi-step LLM analysis.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Solstice System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │   Ingestion  │    │   Gateway    │    │ Fact-Check   │    │
│  │   Pipeline   │    │   Service    │    │   Pipeline   │    │
│  │              │    │              │    │              │    │
│  │ • PDF → Doc  │    │ • LLM Proxy  │    │ • Extract    │    │
│  │ • Layout Det │    │ • Audit Log  │    │ • Verify     │    │
│  │ • Text Ext   │    │ • Retry      │    │ • Present    │    │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    │
│         │                    │                    │            │
│         └────────────────────┴────────────────────┘            │
│                              │                                  │
│                     ┌────────▼────────┐                        │
│                     │  Data Storage   │                        │
│                     │                 │                        │
│                     │ • Cache         │                        │
│                     │ • Documents     │                        │
│                     │ • Evidence      │                        │
│                     └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

## Processing Flow

```
1. Input PDFs (data/clinical_files/)
   - FlublokPI.pdf
   - CDC Influenza vaccines.pdf  
   - Arunachalam et al. (2021).pdf
       ↓
2. Ingestion Pipeline
   - Detectron2 layout detection
   - PyMuPDF text extraction
   - Saves to data/cache/<document_name>/
       ↓
3. Claims File (data/claims/flu_vaccine_claims.json)
   - "Flublok is FDA approved for adults 18 years and older"
   - "Flublok demonstrated 30% better efficacy vs standard dose"
       ↓
4. Fact-Check Pipeline (5 LLM calls per claim)
   - Evidence extraction
   - Quote verification  
   - Completeness check
   - Image analysis
   - Evidence presentation
       ↓
5. Output (data/studies/Flu_Vaccine_Claims_Verification/)
   - study_report.json
   - claim_001/evidence_report.json
   - claim_002/evidence_report.json
```

## Setup

### Prerequisites

- Python 3.11 or 3.12
- Docker
- OpenAI API key  
- Poppler: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)

### Installation

```bash
# Clone repository
git clone <repo-url> && cd solstice

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install
make install-detectron2

# Configure OpenAI
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...

# Start gateway service
make up
```

## Run

```bash
# Process included PDFs into structured documents
python -m src.cli ingest

# Run fact-check on flu vaccine claims
python -m src.cli run-study
```

## What Happens

### 1. PDF Processing (`python -m src.cli ingest`)
- Reads PDFs from `data/clinical_files/`
- Detects layout elements at 400 DPI
- Extracts text preserving medical terminology
- Saves to `data/cache/FlublokPI/extracted/content.json` etc.

### 2. Fact-Checking (`python -m src.cli run-study`)
- Reads claims from `data/claims/flu_vaccine_claims.json`
- For each claim, runs 5 LLM agents sequentially
- Searches all cached documents for evidence
- Outputs to `data/studies/Flu_Vaccine_Claims_Verification/`

### 3. Output Structure
```
claim_001/
├── evidence_report.json     # Final consolidated evidence
├── agent_outputs/
│   ├── evidence_extractor/  # Found passages
│   ├── evidence_verifier/   # Quote verification
│   ├── completeness_check/  # Missing evidence types
│   ├── image_analyzer/      # Figure/table analysis
│   └── evidence_presenter/  # Final formatting
```

## Project Structure

```
solstice/
├── src/
│   ├── cli/                 # Command-line interface
│   ├── injestion/           # PDF processing
│   │   ├── scientific/      # Academic paper pipeline  
│   │   ├── marketing/       # Marketing material pipeline
│   │   └── shared/          # Common components
│   ├── gateway/             # LLM proxy service
│   │   └── app/             # FastAPI application
│   ├── fact_check/          # Fact-checking pipeline
│   │   ├── agents/          # Individual LLM agents
│   │   ├── orchestrators/   # Pipeline coordination
│   │   └── config/          # Model configuration
│   └── interfaces/          # Shared data models
├── data/
│   ├── clinical_files/      # Input PDFs
│   ├── cache/               # Processed documents
│   ├── claims/              # Claim files
│   └── studies/             # Results
├── docker/                  # Docker configurations
└── scripts/                 # Setup utilities
```