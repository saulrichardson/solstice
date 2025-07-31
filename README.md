# Solstice – Clinical Document Fact-Checking Pipeline

Solstice is an LLM-powered pipeline for verifying medical claims against clinical documents. It uses computer vision for PDF layout detection, extracts structured content, and runs multi-step LLM verification.

## System Overview

### Core Services
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

### LLM Pipeline Flow
```
1. PDF Documents
       ↓
2. Ingestion Pipeline
   - Layout detection (Detectron2)
   - Text extraction
   - Figure/table extraction
       ↓
3. Structured Documents (JSON)
       ↓
4. Fact-Check Pipeline (via Gateway)
   - Evidence extraction (LLM)
   - Quote verification (LLM)  
   - Completeness check (LLM)
   - Image analysis (Vision LLM)
   - Evidence presentation (LLM)
       ↓
5. Evidence Report
   - Supporting evidence
   - Contradicting evidence
   - Confidence scores
```

## Quick Start

### Prerequisites

- Python 3.11 or 3.12
- Docker
- OpenAI API key
- Poppler: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Linux)

### Setup

```bash
# Clone and enter directory
git clone <repo-url> && cd solstice

# Install dependencies
make install
make install-detectron2

# Configure API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-...

# Start gateway service
make up
```

### Running Pipelines

#### 1. Ingest PDFs

The repository includes sample PDFs. Process them:

```bash
python -m src.cli ingest
```

This processes all PDFs in `data/clinical_files/` including:
- FlublokPI.pdf
- CDC Influenza vaccines.pdf
- Arunachalam et al. (2021).pdf

#### 2. Run Fact-Check Study

The repository includes example claims. Run the default study:

```bash
python -m src.cli run-study
```

This uses:
- Claims from: `data/claims/flu_vaccine_claims.json`
- Documents: All processed PDFs
- Output: `data/studies/Flu_Vaccine_Claims_Verification/`

### Marketing Pipeline (Complex Layouts)

```bash
python -m src.injestion.marketing.cli <pdf_path> \
  --preset aggressive \
  --box-padding 15.0
```

## Directory Structure

```
data/
├── clinical_files/    # Input PDFs
├── cache/            # Processed documents
├── claims/           # Claim JSON files
└── studies/          # Fact-check results
```

## Common Issues

**Installation fails**: Use Python 3.11.9 via pyenv
```bash
pyenv install 3.11.9
pyenv local 3.11.9
```

**Gateway errors**: Check logs
```bash
make logs
```

**Poor text extraction**: Use higher DPI
```bash
python -m src.cli ingest --dpi 600
```

## Commands Reference

```bash
# Service management
make up        # Start gateway
make down      # Stop gateway
make logs      # View logs

# Processing
python -m src.cli ingest --help      # Ingestion options
python -m src.cli run-study --help   # Fact-check options

# Development
make lint      # Check code
make format    # Format code
make clean     # Clean cache
```