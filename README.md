# Solstice – Clinical Document Fact-Checking Pipeline

Solstice verifies medical claims against clinical documents using computer vision and multi-step LLM analysis.

## What It Does

Takes medical claims like "Flublok is FDA approved for adults 18+" and automatically:
1. Extracts text and images from clinical PDFs using ML layout detection
2. Finds relevant evidence passages via LLM
3. Verifies exact quotes and context
4. Analyzes figures, tables, and charts
5. Produces structured evidence reports

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

## Quick Start

### Prerequisites

- Python 3.11 or 3.12
- Docker
- OpenAI API key  
- Poppler: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)

### Setup (One Time)

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

### Run Example

The repository includes sample PDFs and claims. Just run:

```bash
# Process PDFs (first time only)
python -m src.cli ingest

# Run fact-checking
python -m src.cli run-study
```

Results appear in `data/studies/Flu_Vaccine_Claims_Verification/`

## What's Included

### Sample Documents
- `FlublokPI.pdf` - FDA prescribing information
- `CDC Influenza vaccines.pdf` - CDC guidelines
- `Arunachalam et al. (2021).pdf` - Clinical trial paper

### Sample Claims
- `data/claims/flu_vaccine_claims.json` - Example vaccine efficacy claims

### Output Structure
```
data/studies/Flu_Vaccine_Claims_Verification/
├── study_report.json         # Summary of all claims
├── claim_001/                # Per-claim evidence
│   ├── evidence_report.json  # Structured findings
│   └── agent_outputs/        # Intermediate results
└── claim_002/
    └── ...
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

## Common Tasks

**Check gateway health:**
```bash
make logs
```

**Process your own PDFs:**
```bash
# Add PDFs to data/clinical_files/
python -m src.cli ingest --pdf "YourDocument.pdf"
```

**Create custom claims:**
```json
// data/claims/your_claims.json
{
  "study_name": "Your Study Name",
  "claims": [
    {
      "id": "claim_001", 
      "text": "Your medical claim here"
    }
  ]
}
```

```bash
python -m src.cli run-study --claims data/claims/your_claims.json
```

**Complex layouts (marketing materials):**
```bash
python -m src.injestion.marketing.cli YourBrochure.pdf
```

## Troubleshooting

**Python version issues:** Use pyenv to install Python 3.11.9
**Gateway connection errors:** Verify OPENAI_API_KEY in .env
**Poor text extraction:** Increase DPI with `--dpi 600`

## How It Works

1. **PDF Ingestion**: Detectron2 identifies text blocks, figures, and tables
2. **Content Extraction**: PyMuPDF extracts text while preserving medical terminology
3. **LLM Pipeline** (via Gateway):
   - Evidence extraction finds relevant passages
   - Quote verification ensures accuracy
   - Image analysis processes visual evidence
   - Final presentation consolidates findings
4. **Structured Output**: JSON reports with supporting/contradicting evidence