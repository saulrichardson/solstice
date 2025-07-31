# Solstice – Clinical Document Fact-Checking Pipeline

Solstice is an LLM-powered pipeline for verifying medical claims against clinical documents. It uses computer vision for PDF layout detection, extracts structured content, and runs multi-step LLM verification.

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

Place PDFs in `data/clinical_files/` then run:

```bash
# Process all PDFs
python -m src.cli ingest

# Process specific PDF with options
python -m src.cli ingest --pdf "FlublokPI.pdf" --force
```

#### 2. Run Fact-Check Study

Create claims file `data/claims/example_claims.json`:
```json
{
  "study_name": "Example Study",
  "claims": [
    {
      "id": "claim_001",
      "text": "Your claim text here"
    }
  ]
}
```

Run fact-check:
```bash
# Basic usage
python -m src.cli run-study \
  --claims data/claims/example_claims.json \
  --documents FlublokPI

# Multiple documents
python -m src.cli run-study \
  --claims data/claims/example_claims.json \
  --documents FlublokPI "CDC Influenza vaccines"

# Custom output directory
python -m src.cli run-study \
  --claims data/claims/example_claims.json \
  --documents FlublokPI \
  --output-dir data/studies/my_study
```

Results appear in `data/studies/<study_name>/`

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